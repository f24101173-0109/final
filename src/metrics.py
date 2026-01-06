from typing import Dict, Any
from shapely.geometry import Polygon


def parcel_metrics(poly: Polygon) -> Dict[str, Any]:
    """
    Basic geometry indicators:
    - area
    - width / depth from minimum rotated rectangle (MRR)
    - aspect_ratio = longer/shorter
    """
    area = float(poly.area)
    cen = poly.centroid
    cx, cy = float(cen.x), float(cen.y)

    # minimum rotated rectangle approximates parcel dimensions robustly
    mrr = poly.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)[:-1]  # 4 points

    def dist(a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return (dx * dx + dy * dy) ** 0.5

    # rectangle edges: (0-1,1-2,2-3,3-0)
    e0 = dist(coords[0], coords[1])
    e1 = dist(coords[1], coords[2])

    width = float(max(e0, e1))
    depth = float(min(e0, e1))
    aspect = float(width / depth) if depth > 1e-9 else float("inf")

    return {
        "area": area,
        "centroid_x": cx,
        "centroid_y": cy,
        "width": width,
        "depth": depth,
        "aspect_ratio": aspect,
    }
