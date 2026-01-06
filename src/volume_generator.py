"""
volume_generator.py

Small helper functions for turning a 2D parcel (Shapely Polygon) into a simple
2.5D building mass (extrusion). The basic idea:

- Apply setback (buffer inward) to get a buildable footprint
- Use FAR to estimate number of floors
- Extrude footprint into a prism mesh for quick visualization
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon, MultiPolygon


@dataclass
class VolumeResult:
    buildable_polygon: Polygon
    height: float
    floor_count: int
    buildable_area: float


def compute_buildable_volume(
    polygon: Polygon,
    far: float,
    *,
    setback: float = 0.0,
    floor_height: float = 3.0,
    min_floors: int = 1,
) -> VolumeResult:
    """Compute buildable footprint + floors + height from a parcel and FAR."""
    if far <= 0:
        raise ValueError("FAR must be positive")

    # setback: negative buffer shrinks polygon (inward)
    buildable = polygon.buffer(-setback) if setback else polygon

    if buildable.is_empty or buildable.area <= 1e-9:
        raise ValueError("Setback too large: buildable footprint becomes empty")

    plot_area = polygon.area
    buildable_area = buildable.area

    total_floor_area = plot_area * far

    # floors = total allowable floor area / footprint area
    floors = int(total_floor_area // buildable_area)
    floors = max(floors, min_floors)

    height = floors * floor_height

    return VolumeResult(
        buildable_polygon=buildable,
        height=height,
        floor_count=floors,
        buildable_area=buildable_area,
    )


def extrude_polygon(polygon: Polygon, height: float) -> List[List[Tuple[float, float, float]]]:
    """Extrude a 2D polygon into 3D faces for Matplotlib Poly3DCollection."""
    # If setback/buffer splits the footprint, it can become a MultiPolygon.
    # For quick visualization, keep the largest piece.
    if isinstance(polygon, MultiPolygon):
        parts = list(polygon.geoms)
        parts.sort(key=lambda g: g.area, reverse=True)
        polygon = parts[0]
        
    x_coords, y_coords = polygon.exterior.coords.xy
    coords = list(zip(x_coords, y_coords))[:-1]  # drop closing point

    bottom = [(x, y, 0.0) for x, y in coords]
    top = [(x, y, height) for x, y in coords]

    faces: List[List[Tuple[float, float, float]]] = []
    faces.append(bottom)
    faces.append(top[::-1])

    n = len(coords)
    for i in range(n):
        j = (i + 1) % n
        faces.append([bottom[i], bottom[j], top[j], top[i]])

    return faces


def plot_volume(
    faces,
    height,
    *,
    ax=None,
    show: bool = True,
):
    """
    Plot the extruded volume. If show=True, block until the window is closed.
    """
    faces = list(faces)

    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    color = plt.cm.viridis(min(height / 50.0, 1.0))
    poly = Poly3DCollection(faces, facecolors=color, edgecolor="k", alpha=0.85)
    ax.add_collection3d(poly)

    xs, ys, zs = [], [], []
    for face in faces:
        for x, y, z in face:
            xs.append(x)
            ys.append(y)
            zs.append(z)

    pad = 1.0
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_zlim(0.0, max(zs) + pad)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(f"Volume (h={height:.1f})")

    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs)
    ax.set_box_aspect([max(dx, 1e-6), max(dy, 1e-6), max(dz, 1e-6)])

    fig.tight_layout()

    if show:
        plt.show(block=True)

    return ax



if __name__ == "__main__":
    # quick local test
    from shapely.geometry import box

    parcel = box(0, 0, 50, 40)
    result = compute_buildable_volume(parcel, far=2.5, setback=5.0, floor_height=3.5)

    print("Buildable area:", round(result.buildable_area, 2))
    print("Floors:", result.floor_count)
    print("Height:", round(result.height, 2))

    faces = extrude_polygon(result.buildable_polygon, result.height)
    ax = plot_volume(faces, result.height, show=True)

    # optional save
    ax.get_figure().savefig("example_volume.png", dpi=150)
