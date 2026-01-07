from __future__ import annotations

from typing import List, Dict, Any, Callable, Tuple, Optional
from pathlib import Path
import csv
import math
import re

from shapely import affinity
from shapely.geometry import Polygon, MultiPolygon

from metrics import parcel_metrics
from volume_generator import extrude_polygon


# -----------------------------
# Parsing helpers
# -----------------------------
def _to_number(x: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Parse numbers from: 60, '60', '60%', '60*', ' 180 % ', '250*' ...
    Return default if cannot parse.
    """
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()
    if not s:
        return default

    s = s.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if not m:
        return default
    try:
        return float(m.group(0))
    except ValueError:
        return default


def _to_ratio(x: Any, default: float = 0.6) -> float:
    """
    建蔽率 building_r:
    - allow 0~1 ratio
    - allow 0~100 percent style (60 / '60%' -> 0.6)
    """
    v = _to_number(x, default=default)
    if v is None:
        v = default
    if v > 1.0:
        v = v / 100.0
    return max(0.0, min(v, 1.0))


def _to_far(x: Any, default: float = 2.5) -> float:
    """
    容積率 floor_r:
    - if given as '180%' -> 1.8
    - if given as 2.5 -> 2.5
    - if given as 180 (percent style) -> 1.8
    """
    v = _to_number(x, default=default)
    if v is None:
        v = default
    # percent-style guard
    if v > 10.0:
        v = v / 100.0
    return max(0.0, v)


# -----------------------------
# Geometry helpers
# -----------------------------
def _largest_polygon(geom: Polygon | MultiPolygon) -> Polygon:
    """If MultiPolygon, keep the largest non-empty piece."""
    if isinstance(geom, MultiPolygon):
        parts = [g for g in geom.geoms if (not g.is_empty and g.area > 1e-9)]
        if not parts:
            raise ValueError("MultiPolygon has no non-empty parts.")
        return max(parts, key=lambda g: g.area)
    return geom


def _scale_to_area(poly: Polygon, target_area: float) -> Polygon:
    """
    Uniformly scale polygon about centroid to match target area.
    Only SHRINK (never enlarge beyond buildable boundary).
    """
    if poly.is_empty or poly.area <= 1e-9:
        return poly
    if target_area <= 1e-9:
        return poly.buffer(-1e9)  # empty-ish

    scale = math.sqrt(min(target_area / poly.area, 1.0))
    return affinity.scale(poly, xfact=scale, yfact=scale, origin="centroid")


# -----------------------------
# Main batch
# -----------------------------
def run_batch(
    parcels: List[Tuple[str, Polygon, Dict[str, Any]]],
    far_rule: Callable[[Dict[str, Any]], float],  # keep for compatibility
    *,
    setback: float = 0.5,
    floor_height: float = 3.6,
    min_floors: int = 1,
    max_floors: int = 60,          # ✅ 防止一棟爆高毀全圖
    fallback_bcr: float = 0.6,     # ✅ 沒有 building_r 時
    fallback_far: float = 2.5,     # ✅ 沒有 floor_r 時
) -> Dict[str, Any]:
    """
    Returns dict with:
    - rows: list of per-parcel result dicts
    - buildings: list of (pid, footprint_polygon, height, faces)
    """
    rows: List[Dict[str, Any]] = []
    buildings: List[Tuple[str, Polygon, float, Any]] = []

    for pid, geom, props in parcels:
        poly = _largest_polygon(geom)

        # metrics (for csv)
        m = parcel_metrics(poly)

        # --- read from GeoJSON first; fallback to far_rule if floor_r missing ---
        bcr = _to_ratio(props.get("building_r", fallback_bcr), default=fallback_bcr)

        if "floor_r" in props and props.get("floor_r") not in (None, ""):
            far = _to_far(props.get("floor_r"), default=fallback_far)
        else:
            # fallback to rule-based far (old pipeline)
            try:
                far = float(far_rule(m))
            except Exception:
                far = fallback_far

        # buildable boundary with setback
        buildable = poly.buffer(-setback) if setback else poly
        if buildable.is_empty or buildable.area <= 1e-9:
            buildable = poly  # fallback: no setback
        buildable = _largest_polygon(buildable)

        # footprint must match BCR, but stay inside buildable
        plot_area = max(poly.area, 1e-9)
        target_fp_area = plot_area * bcr
        footprint = _scale_to_area(buildable, target_fp_area)

        if footprint.is_empty or footprint.area <= 1e-9:
            footprint = buildable

        # floors from FAR using footprint area
        total_floor_area = plot_area * far
        fp_area = max(footprint.area, 1e-9)

        floors = int(math.ceil(total_floor_area / fp_area))
        floors = max(floors, min_floors)
        floors = min(floors, max_floors)  # ✅ clamp

        height = floors * floor_height

        faces = extrude_polygon(footprint, height)

        row = {
            "id": pid,
            "area": m.get("area", poly.area),
            "width": m.get("width"),
            "depth": m.get("depth"),
            "aspect_ratio": m.get("aspect_ratio"),
            "building_r": bcr,
            "floor_r": far,
            "setback": setback,
            "footprint_area": footprint.area,
            "floors": floors,
            "floor_height": floor_height,
            "height": height,
        }
        rows.append(row)
        buildings.append((pid, footprint, height, faces))

    return {"rows": rows, "buildings": buildings}


def save_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
