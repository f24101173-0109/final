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

    # ---- 3D batch view (keep ONLY this window) ----
    from viz3d import plot_site_massing_3d

    # 只跳一張成果圖，先留這個 show=True
    plot_site_massing_3d(
        parcels,
        out_a["buildings"],
        title="Batch Volume (rule: area)",
        save_path="outputs/batch_massing_rule_area_3d.png",
        show=True,          # 只留這個 True
        unit="m",
        max_buildings=300,
    )

    # 其他 3D 圖：只存檔，不跳窗
    plot_site_massing_3d(
        parcels,
        out_b["buildings"],
        title="Batch Volume (rule: frontage)",
        save_path="outputs/batch_massing_rule_frontage_3d.png",
        show=False,
        unit="m",
        max_buildings=300,
    )

    # 這兩段先不要（它們會再開視窗）
    # from volume_generator import plot_batch_volumes
    # plot_batch_volumes(out_a["buildings"], title="Batch Volume (rule: area)", show=True, max_buildings=300)

    # ---- 3D export (OBJ) ----
    from export_3d import export_obj
    export_obj(out_a["buildings"], "outputs/site_mass_rule_area.obj", show=False)   # ✅ 不跳 viewer
    export_obj(out_b["buildings"], "outputs/site_mass_rule_frontage.obj", show=False)

    # 這段也先不要（又會再開一個 3D 視窗）
    # from volume_generator import plot_batch_volumes
    # plot_batch_volumes(
    #     out_a["buildings"],
    #     base_parcels=parcels,
    #     title="Batch massing (BCR+FAR from GeoJSON)",
    #     show=True,
    #     save_path="outputs/batch_massing_3d.png",
    # )


if __name__ == "__main__":
    main()
