from __future__ import annotations
from typing import List, Tuple
import numpy as np
import trimesh

Face = List[Tuple[float, float, float]]
Building = Tuple[str, object, float, List[Face]]

def buildings_to_trimesh(buildings: List[Building]) -> trimesh.Trimesh:
    vertices = []
    faces = []
    v_offset = 0

    for pid, footprint, height, polys in buildings:
        for poly in polys:
            pts = np.array(poly, dtype=float)
            if len(pts) < 3:
                continue

            vertices.append(pts)
            for i in range(1, len(pts) - 1):
                faces.append([v_offset, v_offset + i, v_offset + i + 1])

            v_offset += len(pts)

    V = np.vstack(vertices)
    F = np.array(faces, dtype=int)

    mesh = trimesh.Trimesh(vertices=V, faces=F, process=True)

    # Make it robust across trimesh versions
    try:
        mesh.merge_vertices()
    except Exception:
        pass

    try:
        mesh.remove_unreferenced_vertices()
    except Exception:
        pass

    return mesh



def export_obj(buildings, out_path: str, show: bool = False):
    mesh = buildings_to_trimesh(buildings)
    mesh.export(out_path)

    if show:
        mesh.show()  

    print(f"3D exported: {out_path}")

