from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
from shapely.geometry import Polygon


def plot_height_map(
    buildings: List[Tuple[str, Polygon, float]],
    out_png: str,
    title: str,
) -> None:
    """
    buildings: list of (id, footprint_polygon, height)
    """
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)

    heights = [h for _, _, h in buildings]
    hmax = max(heights) if heights else 1.0

    fig, ax = plt.subplots(figsize=(10, 8))
    for pid, poly, h in buildings:
        x, y = poly.exterior.xy
        c = plt.cm.viridis(min(h / hmax, 1.0))
        ax.fill(x, y, color=c, alpha=0.85, linewidth=0.8, edgecolor="black")

    ax.set_aspect("equal", "box")
    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
