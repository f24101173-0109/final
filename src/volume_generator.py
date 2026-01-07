"""
volume_generator.py

Small helper functions for turning a 2D parcel (Shapely Polygon/MultiPolygon)
into a simple 2.5D building mass (extrusion).

Pipeline idea:
- Apply setback (buffer inward) to get a buildable footprint
- Use FAR to estimate number of floors
- Extrude footprint into a prism mesh for quick visualization (Matplotlib)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry

import matplotlib as mpl

import numpy as np
from shapely.geometry import Polygon, MultiPolygon

def plot_batch_volumes(
    buildings,
    *,
    base_parcels=None,   # optional: list of (pid, polygon, props) from GeoJSON
    title: str = "Batch Massing",
    show: bool = True,
    save_path: str | None = None,
    ax=None,
):
    """
    buildings: list of (pid, footprint_polygon, height, faces)
    base_parcels: list of (pid, polygon, props) to draw as 2D base map
    """
    if ax is None:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    # ---- 1) draw base map (2D parcels on z=0) ----
    if base_parcels is not None:
        for pid, geom, props in base_parcels:
            g = geom
            if isinstance(g, MultiPolygon):
                g = max(list(g.geoms), key=lambda x: x.area)

            x, y = g.exterior.coords.xy
            ax.plot(x, y, zs=0.0, color="0.4", linewidth=0.8, alpha=0.9)

            # optional: light fill using a thin "polygon" face at z=0
            coords2d = list(zip(x, y))[:-1]
            face0 = [(xx, yy, 0.0) for (xx, yy) in coords2d]
            ax.add_collection3d(
                Poly3DCollection([face0], facecolors="0.9", edgecolors="none", alpha=0.15)
            )

    # ---- 2) draw buildings with height colormap ----
    heights = [h for (_, _, h, _) in buildings]
    hmin, hmax = (min(heights), max(heights)) if heights else (0.0, 1.0)
    cmap = plt.cm.viridis
    norm = plt.Normalize(vmin=hmin, vmax=hmax)

    all_x, all_y, all_z = [], [], []

    for pid, footprint, height, faces in buildings:
        color = cmap(norm(height))
        poly = Poly3DCollection(faces, facecolors=color, edgecolor="k", alpha=0.85, linewidths=0.3)
        ax.add_collection3d(poly)

        # --- ADD COLORBAR (Height Legend) ---
        norm = mpl.colors.Normalize(vmin=0, vmax=height)
        sm = mpl.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
        sm.set_array([])

        cbar = ax.get_figure().colorbar(
            sm,
            ax=ax,
            fraction=0.03,
            pad=0.1
        )
        cbar.set_label("Building Height (m)")


        for face in faces:
            for x, y, z in face:
                all_x.append(x)
                all_y.append(y)
                all_z.append(z)

    # ---- 3) bounds + aspect ----
    if all_x and all_y:
        pad = 1.0
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
        ax.set_zlim(0.0, (max(all_z) if all_z else 1.0) + pad)

        dx = max(all_x) - min(all_x)
        dy = max(all_y) - min(all_y)
        dz = max(all_z) if all_z else 1.0
        ax.set_box_aspect([max(dx, 1e-6), max(dy, 1e-6), max(dz, 1e-6)])

    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    # ---- 4) legend (colorbar) ----
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Building Height(m)")

    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=160)

    if show:
        plt.show()

    return ax


@dataclass
class VolumeResult:
    buildable_polygon: BaseGeometry  # Polygon or MultiPolygon
    height: float
    floor_count: int
    buildable_area: float


def _largest_polygon(geom: BaseGeometry) -> Polygon:
    """
    Return a single Polygon for extrusion:
    - If geom is Polygon: return it
    - If geom is MultiPolygon: return the largest piece
    Raises ValueError if empty / not polygon-like.
    """
    if geom is None or geom.is_empty:
        raise ValueError("Empty geometry (cannot extrude).")

    if isinstance(geom, Polygon):
        return geom

    if isinstance(geom, MultiPolygon):
        parts = [g for g in geom.geoms if (not g.is_empty and g.area > 0)]
        if not parts:
            raise ValueError("MultiPolygon has no non-empty parts.")
        return max(parts, key=lambda g: g.area)

    raise ValueError(f"Unsupported geometry type for extrusion: {type(geom)}")


def compute_buildable_volume(
    polygon: BaseGeometry,
    far: float,
    *,
    setback: float = 0.0,
    floor_height: float = 3.0,
    min_floors: int = 1,
) -> VolumeResult:
    """Compute buildable footprint + floors + height from a parcel and FAR."""
    if far <= 0:
        raise ValueError("FAR must be positive")
    if floor_height <= 0:
        raise ValueError("floor_height must be positive")
    if min_floors < 1:
        raise ValueError("min_floors must be >= 1")

    if polygon is None or polygon.is_empty:
        raise ValueError("Input parcel geometry is empty")

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


def extrude_polygon(geom: BaseGeometry, height: float) -> List[List[Tuple[float, float, float]]]:
    """Extrude a (Multi)Polygon into 3D faces for Matplotlib Poly3DCollection."""
    if height <= 0:
        raise ValueError("height must be positive")

    poly = _largest_polygon(geom)

    # Exterior ring only (ignore holes for now: quick massing)
    x_coords, y_coords = poly.exterior.coords.xy
    coords2d = list(zip(x_coords, y_coords))[:-1]  # drop closing point

    if len(coords2d) < 3:
        raise ValueError("Polygon exterior has fewer than 3 vertices")

    bottom = [(x, y, 0.0) for x, y in coords2d]
    top = [(x, y, height) for x, y in coords2d]

    faces: List[List[Tuple[float, float, float]]] = []
    faces.append(bottom)
    faces.append(top[::-1])

    n = len(coords2d)
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
    """Plot a single extruded volume."""
    faces = list(faces)

    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    color = plt.cm.viridis(min(float(height) / 50.0, 1.0))
    poly = Poly3DCollection(faces, facecolors=color, edgecolor="k", alpha=0.85,shade=True)
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
    ax.set_title(f"Volume (h={float(height):.1f})")

    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs)
    ax.set_box_aspect([max(dx, 1e-6), max(dy, 1e-6), max(dz, 1e-6)])

    fig.tight_layout()

    if show:
        plt.show(block=True)

    return ax


def plot_batch_volumes(
    buildings,
    *,
    title: str = "Batch Volume",
    show: bool = True,
    ax=None,
    max_buildings: Optional[int] = None,
):
    """
    Plot many buildings in one Matplotlib 3D figure.

    buildings: list of tuples like (pid, buildable_polygon, height, faces)
    """
    if max_buildings is not None:
        buildings = buildings[:max_buildings]

    if ax is None:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    xs, ys, zs = [], [], []

    for pid, poly, height, faces in buildings:
        # color by height
        color = plt.cm.viridis(min(float(height) / 80.0, 1.0))
        poly3d = Poly3DCollection(
            faces,
            facecolors=color,
            edgecolor="k",
            linewidths=0.2,
            alpha=0.85,
        )
        ax.add_collection3d(poly3d)

        for face in faces:
            for x, y, z in face:
                xs.append(x)
                ys.append(y)
                zs.append(z)

    if not xs:
        raise ValueError("No geometry to plot (buildings list is empty?)")

    pad = 1.0
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_zlim(0.0, max(zs) + pad)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)

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

    ax.get_figure().savefig("example_volume.png", dpi=150)
