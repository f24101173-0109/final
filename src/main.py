from shapely.geometry import box
from volume_generator import (
    compute_buildable_volume,
    extrude_polygon,
    plot_volume
)


def main():
    # Demo parcel
    parcel = box(0, 0, 60, 40)

    far = 3.0
    setback = 3.0
    floor_height = 3.6

    result = compute_buildable_volume(
        parcel,
        far=far,
        setback=setback,
        floor_height=floor_height,
        min_floors=1
    )

    faces = extrude_polygon(result.buildable_polygon, result.height)
    plot_volume(faces, result.height,show=True)


if __name__ == "__main__":
    main()
