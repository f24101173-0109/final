"""
B-side runner: load parcels -> compute metrics -> apply rules -> generate massing -> export results.

AI assistance prompt (for course transparency):
- "Help me build a batch pipeline that reads parcel GeoJSON, computes simple parcel metrics,
   applies rule-based FAR, and generates 2.5D massing outputs with Shapely and Matplotlib."
"""

from io_geojson import load_parcels_geojson
from rules import far_rule_area, far_rule_frontage
from batch_massing import run_batch, save_csv
from viz2d import plot_height_map


def main():
    # TODO: change this to your real file path
    geojson_path = "data/parcels.geojson"

    parcels = load_parcels_geojson(geojson_path)

    # Rule set A
    out_a = run_batch(parcels, far_rule_area, setback=0.5, floor_height=3.6)
    save_csv(out_a["rows"], "outputs/result_rule_area.csv")
    buildings_a = [(pid, poly, h) for (pid, poly, h, _faces) in out_a["buildings"]]
    plot_height_map(buildings_a, "outputs/height_map_rule_area.png", "Height map (Rule A: FAR by area)")

    # Rule set B
    out_b = run_batch(parcels, far_rule_frontage, setback=0.5, floor_height=3.6)
    save_csv(out_b["rows"], "outputs/result_rule_frontage.csv")
    buildings_b = [(pid, poly, h) for (pid, poly, h, _faces) in out_b["buildings"]]
    plot_height_map(buildings_b, "outputs/height_map_rule_frontage.png", "Height map (Rule B: FAR by frontage/shape)")

    print("Done. Check outputs/ for PNG + CSV.")

    # ---- 3D export (OBJ) ----
    from export_3d import export_obj

    export_obj(out_a["buildings"], "outputs/site_mass_rule_area.obj", show=True)
    export_obj(out_b["buildings"], "outputs/site_mass_rule_frontage.obj")



if __name__ == "__main__":
    main()
