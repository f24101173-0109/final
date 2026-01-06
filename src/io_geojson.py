import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

from shapely.geometry import shape, Polygon, MultiPolygon


def load_parcels_geojson(path: str) -> List[Tuple[str, Polygon, Dict[str, Any]]]:
    """
    Load parcel polygons from GeoJSON. Supports Polygon and MultiPolygon.
    For MultiPolygon, we keep the largest polygon (by area).
    Returns list of (parcel_id, polygon, properties).
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))

    feats = data.get("features", [])
    out: List[Tuple[str, Polygon, Dict[str, Any]]] = []

    type_counter: Dict[str, int] = {}

    for i, f in enumerate(feats):
        geom = f.get("geometry")
        props = f.get("properties", {}) or {}
        if not geom:
            continue

        g = shape(geom)
        gtype = g.geom_type
        type_counter[gtype] = type_counter.get(gtype, 0) + 1

        poly: Polygon | None = None

        if isinstance(g, Polygon):
            poly = g
        elif isinstance(g, MultiPolygon):
            # pick the largest piece
            parts = list(g.geoms)
            parts.sort(key=lambda x: x.area, reverse=True)
            poly = parts[0] if parts else None
        else:
            # skip non-area geometry
            continue

        if poly is None or poly.is_empty or poly.area <= 1e-9:
            continue

        pid = str(props.get("id", props.get("ID", i)))
        out.append((pid, poly, props))

    if not out:
        raise ValueError(
            f"No Polygon/MultiPolygon found. Geometry types in file: {type_counter}"
        )

    return out
