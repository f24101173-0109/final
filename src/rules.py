from typing import Dict, Any


def far_rule_area(m: Dict[str, Any]) -> float:
    """Rule set A: FAR by parcel area tiers."""
    a = m["area"]
    if a < 600:
        return 1.8
    if a < 1200:
        return 2.6
    if a < 2500:
        return 3.2
    return 4.0


def far_rule_frontage(m: Dict[str, Any]) -> float:
    """Rule set B: FAR by frontage/shape (use width + aspect)."""
    w = m["width"]
    ar = m["aspect_ratio"]

    # wide parcels can take more intensive development
    if w >= 30:
        return 4.0
    if w >= 20:
        return 3.2

    # very long/thin parcels are usually less efficient
    if ar >= 3.5:
        return 2.0

    return 2.6
