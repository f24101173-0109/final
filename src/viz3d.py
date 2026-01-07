# src/viz3d.py
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import MultiPolygon

from volume_generator import extrude_polygon


def plot_site_massing_3d(
    parcels,
    buildings,
    *,
    title="Batch massing (3D)",
    save_path=None,
    show=True,
    unit="m",
    max_buildings=300,
    elev=25,
    azim=-60,
):
    """
    parcels: [(pid, geom, props), ...] from load_parcels_geojson
    buildings: [(pid, footprint, height, faces), ...] from run_batch

    - draws parcel outlines as base map at z=0
    - draws extruded buildings colored by height
    - adds a colorbar with unit
    - optionally saves PNG and optionally shows a window
    """

    # limit for performance
    buildings = list(buildings)[:max_buildings]

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    # ---- 1) base map (parcel outlines + faint fill at z=0) ----
    for pid, geom, props in parcels:
        g = geom
        if isinstance(g, MultiPolygon):
            g = max(list(g.geoms), key=lambda x: x.area)

        x, y = g.exterior.coords.xy
        ax.plot(x, y, zs=0.0, color="0.4", linewidth=0.8, alpha=0.9)

        coords = list(zip(x, y))[:-1]
        face0 = [(xx, yy, 0.0) for (xx, yy) in coords]
        ax.add_collection3d(
            Poly3DCollection([face0], facecolors="0.9", edgecolors="none", alpha=0.12)
        )

    # ---- 2) buildings ----
    heights = [h for (_, _, h, _faces) in buildings]
    if not heights:
        raise ValueError("No buildings to plot.")

    hmin, hmax = min(heights), max(heights)
    cmap = plt.cm.viridis
    norm = plt.Normalize(vmin=hmin, vmax=hmax)

    all_x, all_y, all_z = [], [], []

    for pid, footprint, height, faces in buildings:
        if faces is None:
            faces = extrude_polygon(footprint, height)

        color = cmap(norm(height))
        poly = Poly3DCollection(
            faces, facecolors=color, edgecolor="k", alpha=0.85, linewidths=0.25
        )
        ax.add_collection3d(poly)

        for face in faces:
            for x, y, z in face:
                all_x.append(x)
                all_y.append(y)
                all_z.append(z)

    # ---- 3) bounds + view ----
    pad = 1.0
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
    ax.set_zlim(0.0, max(all_z) + pad)

    dx = max(all_x) - min(all_x)
    dy = max(all_y) - min(all_y)
    dz = max(all_z)
    ax.set_box_aspect([max(dx, 1e-6), max(dy, 1e-6), max(dz, 1e-6)])

    ax.view_init(elev=elev, azim=azim)

    ax.set_title(title)
    ax.set_xlabel(f"X ({unit})")
    ax.set_ylabel(f"Y ({unit})")
    ax.set_zlabel(f"Z ({unit})")

    # ---- 4) colorbar ----
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label(f"Building Height ({unit})")

    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=180)

    if show:
        plt.show()
    else:
        # 不跳視窗就關掉 figure，避免卡住或多開視窗
        plt.close(fig)

    return ax
