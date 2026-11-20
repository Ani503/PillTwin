import pytest
from src.parsers.canonical import parse_composition, parse_pack_size, normalize_strength

def test_pack_size_parsing():
    cases = [
        ("strip of 10 tablets", (10, "tablet")),
        ("strip of 15 capsules", (15, "capsule")),
        ("strip of 30 Tablet pr", (30, "units")),
        ("10's", (10, "units")),
        ("15's", (15, "units")),
        ("14'S", (14, "units")),
        ("100's", (100, "units")),
        ("bottle of 100 tablets", (100, "units")),
        ("10 tablets", (10, "units")),
        ("strip of 6 tablets", (6, "tablet"))
    ]
    for label, expected in cases:
        cnt, unit = parse_pack_size(label)
        assert cnt == expected[0], f"Failed count for '{label}': got {cnt}, expected {expected[0]}"

def test_strength_normalization():
    assert normalize_strength("500", "mg") == "500mg"
    assert normalize_strength("500.0", "mg") == "500mg"
    assert normalize_strength("0.50", "mg") == "0.5mg"
    assert normalize_strength("1", "g") == "1000mg"
    assert normalize_strength("1000", "mcg") == "1000mcg"
    assert normalize_strength("1000", "iu") == "1000iu"
    assert normalize_strength("0.03", "mg") == "0.03mg"

def test_diverse_compositions():
    # Arkamin: Clonidine (100mcg)
    res = parse_composition("Clonidine (100mcg)", form_hint="strip of 30 tablets")
    assert res.is_solid_oral
    assert res.canonical_key == "clonidine:100mcg|tablet|IR"

    # Augmentin 625 Duo: Amoxycillin (500mg) + Clavulanic Acid (125mg)
    aug = parse_composition("Amoxycillin (500mg) + Clavulanic Acid (125mg)", form_hint="strip of 10 tablets")
    assert aug.is_solid_oral
    assert aug.canonical_key == "amoxicillin:500mg;clavulanic acid:125mg|tablet|IR"

    # Altraday Capsule SR: Aceclofenac (200mg) + Rabeprazole (20mg) SR
    sr_cap = parse_composition("Aceclofenac (200mg) + Rabeprazole (20mg)", form_hint="strip of 10 capsule sr")
    assert sr_cap.is_solid_oral
    assert sr_cap.dosage_form == "capsule"
    assert sr_cap.release_type == "ER"
    assert sr_cap.canonical_key == "aceclofenac:200mg;rabeprazole:20mg|capsule|ER"
