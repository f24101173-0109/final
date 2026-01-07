import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import MultiPolygon

from io_geojson import load_parcels_geojson
from batch_massing import run_batch
from rules import far_rule_area  # 你現在 run_b.py 用的那個 rule
from volume_generator import extrude_polygon

def plot_base(ax, parcels):
    # 2D 底圖：地塊外框 + 淡填色 (z=0)
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

def plot_buildings(ax, buildings):
    heights = [h for (_, _, h, _) in buildings]
    hmin, hmax = min(heights), max(heights)

    cmap = plt.cm.viridis
    norm = plt.Normalize(vmin=hmin, vmax=hmax)

    all_x, all_y, all_z = [], [], []

    for pid, footprint, height, faces in buildings:
        color = cmap(norm(height))
        poly = Poly3DCollection(
            faces, facecolors=color, edgecolor="k", alpha=0.85, linewidths=0.25
        )
        ax.add_collection3d(poly)

        for face in faces:
            for x, y, z in face:
                all_x.append(x); all_y.append(y); all_z.append(z)

    # bounds
    pad = 1.0
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
    ax.set_zlim(0.0, max(all_z) + pad)

    dx = max(all_x) - min(all_x)
    dy = max(all_y) - min(all_y)
    dz = max(all_z)
    ax.set_box_aspect([max(dx, 1e-6), max(dy, 1e-6), max(dz, 1e-6)])

    # colorbar 圖例
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    return sm

def main():
    geojson_path = "data/parcels.geojson"  # 實際 geojson 路徑

    parcels = load_parcels_geojson(geojson_path)
    out = run_batch(parcels, far_rule_area, setback=0.5, floor_height=3.6)

    # buildings 的 faces 如果你存的不是 faces，就在這裡重算一次
    buildings = []
    for pid, fp, h, faces in out["buildings"]:
        if faces is None:
            faces = extrude_polygon(fp, h)
        buildings.append((pid, fp, h, faces))

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    plot_base(ax, parcels)
    sm = plot_buildings(ax, buildings)

    ax.set_title("Batch massing with base map + legend")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Height")

    fig.tight_layout()
    fig.savefig("outputs/batch_massing_with_basemap.png", dpi=180)
    plt.show()

if __name__ == "__main__":
    main()
