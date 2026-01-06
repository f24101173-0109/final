from typing import List, Dict, Any, Callable, Tuple
from pathlib import Path
import csv

from shapely.geometry import Polygon, MultiPolygon

from metrics import parcel_metrics
from volume_generator import compute_buildable_volume, extrude_polygon


def run_batch(
    parcels: List[Tuple[str, Polygon, Dict[str, Any]]],
    far_rule: Callable[[Dict[str, Any]], float],
    *,
    setback: float = 3.0,
    floor_height: float = 3.6,
    min_floors: int = 1,
) -> Dict[str, Any]:
    """
    Returns dict with:
    - rows: list of per-parcel result dicts
    - buildings: list of (pid, buildable_polygon, height, faces)
    """
    rows = []
    buildings = []

    for pid, poly, props in parcels:
        if isinstance(poly, MultiPolygon):
            parts = list(poly.geoms)
            parts.sort(key=lambda g: g.area, reverse=True)
            poly = parts[0]

        m = parcel_metrics(poly)
        far = float(far_rule(m))

        res = compute_buildable_volume(
            poly,
            far=far,
            setback=setback,
            floor_height=floor_height,
            min_floors=min_floors,
        )

        faces = extrude_polygon(res.buildable_polygon, res.height)

        row = {
            "id": pid,
            "area": m["area"],
            "width": m["width"],
            "depth": m["depth"],
            "aspect_ratio": m["aspect_ratio"],
            "far_used": far,
            "buildable_area": res.buildable_area,
            "floors": res.floor_count,
            "height": res.height,
        }
        rows.append(row)
        buildings.append((pid, res.buildable_polygon, res.height, faces))

    return {"rows": rows, "buildings": buildings}


def save_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
