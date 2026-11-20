import pytest
from src.matching.engine import PillTwinEngine, MANDATORY_DISCLAIMER

@pytest.fixture(scope="module")
def engine():
    return PillTwinEngine(
        brand_parquet_path="data/processed/brand_clean.parquet",
        formulary_json_path="data/processed/formulary_index.json",
        calibration_json_path="data/processed/matcher_calibration.json",
        caution_config_path="config/caution_drugs.yaml",
        abstention_threshold=0.75
    )

class TestPillTwinMatchingEngine:
    def test_exact_match_augmentin_625(self, engine):
        result = engine.match_item("Augmentin 625 Duo Tablet")
        assert result.match_type in ("exact", "match on assumed release; confirm on strip")
        assert result.brand is not None
        assert "Augmentin" in result.brand['name']
        assert result.generic is not None
        assert "Amoxycillin" in result.generic['name'] or "Amoxicillin" in result.generic['name']
        assert "125mg" in result.generic['name']
        assert result.saving_per_unit is not None and result.saving_per_unit > 0
        assert result.saving_percent is not None and result.saving_percent > 0
        assert result.generic['price_list_date'] == "2026-11-07"
        assert result.disclaimer == MANDATORY_DISCLAIMER

    def test_typo_tolerance_brand_matching(self, engine):
        # Typo: 'Augmentn 625 Duo' (missing 'i' in Augmentin)
        res1 = engine.match_item("Augmentn 625 Duo")
        assert res1.brand is not None
        assert "Augmentin 625" in res1.brand['name']
        assert res1.match_type in ("exact", "match on assumed release; confirm on strip")

        # Typo: 'Azithral 500' -> Azithral 500 Tablet
        res2 = engine.match_item("Azithral 500")
        assert res2.brand is not None
        assert "Azithral 500" in res2.brand['name']
        assert res2.match_type in ("exact", "match on assumed release; confirm on strip")

    def test_abstention_on_gibberish_query(self, engine):
        # Nonsense input must abstain with match_type='uncertain'
        res = engine.match_item("XyzRandomNonsenseString 999")
        assert res.match_type == "uncertain"
        assert res.generic is None
        assert res.saving_per_unit is None
        assert len(res.candidates) > 0 or res.reason is not None

    def test_unsupported_dosage_form_rejected(self, engine):
        # Ascoril LS is a liquid syrup
        res = engine.match_item("Ascoril LS Syrup")
        assert res.match_type == "unsupported"
        assert "not supported yet" in res.reason.lower()
        assert res.generic is None

    def test_caution_drug_supervision_notice(self, engine):
        # Uniwarfin 5mg (Warfarin - NTI caution drug)
        res = engine.match_item("Uniwarfin 5mg Tablet")
        assert res.match_type in ("exact", "match on assumed release; confirm on strip")
        assert res.has_caution is True
        assert len(res.caution_flags) > 0
        assert "NEEDS PHARMACIST REVIEW" in res.caution_message
        assert res.caution_flags[0]['id'] == 'warfarin'

        # Paracetamol (regular non-caution drug)
        res_pcm = engine.match_item("Dolo 650 Tablet")
        assert res_pcm.match_type == "match on assumed release; confirm on strip"
        assert res_pcm.has_caution is False
        assert res_pcm.caution_message is None

    def test_user_confirmed_brand_flow(self, engine):
        # Rule 4: User explicitly confirms a name from the editable list
        res = engine.match_item(query="obscure noisy input", confirmed_brand="Augmentin 625 Duo Tablet")
        assert res.match_type in ("exact", "match on assumed release; confirm on strip")
        assert res.brand['name'] == "Augmentin 625 Duo Tablet"
        assert res.generic is not None

    def test_dolo_650_match_on_assumed_release(self, engine):
        # Dolo 650: release is unstated (assumed IR) -> returns 'match on assumed release; confirm on strip'
        res = engine.match_item("Dolo 650 Tablet")
        assert res.match_type == "match on assumed release; confirm on strip"
        assert res.brand is not None
        assert res.brand['release_type_source'] == "assumed"
        assert res.generic is not None
        assert "paracetamol" in res.generic['name'].lower()
        assert res.saving_per_unit is not None

    def test_pan_40_unstated_release_returns_uncertain(self, engine):
        # Pan 40: Pantoprazole is a commonly DR/ER drug (PPI). Unstated release returns 'uncertain: release unknown'
        res = engine.match_item("PAN 40 Tablet")
        assert res.match_type == "uncertain"
        assert "release unknown" in res.reason
        assert res.generic is None

    def test_duplicate_key_uses_higher_price_and_ambiguous_flag(self, engine):
        # Dasatinib 50mg has two catalog entries (Code 2412 ₹36.9532/u vs Code 2302 ₹17.1875/u)
        key = "dasatinib:50mg|tablet|IR"
        assert key in engine.formulary
        options = engine.formulary[key]
        assert len(options) == 2
        # Highest price per unit must be first (conservative pricing rule)
        assert options[0]['drug_code'] == "2412"
        assert options[0]['price_per_unit'] > options[1]['price_per_unit']
        assert options[0]['is_price_ambiguous'] is True
        assert options[0]['price_status'] == "price ambiguous"

    def test_prescription_multi_item_totals(self, engine):
        prescription_items = [
            {"name": "Augmentin 625 Duo Tablet", "units_needed": 10},
            {"name": "Dolo 650 Tablet", "units_needed": 15},
            {"name": "PAN 40 Tablet", "units_needed": 30}
        ]

        summary = engine.match_prescription(prescription_items, days_of_use=30)
        assert summary.total_items == 3
        # Augmentin and Dolo match on assumed release (2 matches); PAN 40 returns uncertain (1 uncertain)
        assert summary.exact_matches_count == 2
        assert summary.uncertain_count == 1
        assert summary.total_brand_cost > summary.total_generic_cost
        assert summary.total_saving > 0
        assert summary.overall_saving_percent > 0
        assert summary.price_list_date == "2026-11-07"
        assert summary.disclaimer == MANDATORY_DISCLAIMER

    def test_get_data_info_dates_and_note(self, engine):
        info = engine.get_data_info()
        assert info["price_list_export_date"] == "2026-11-07"
        assert info["price_list_date_source"] == "PDF creation date; official effective date not stated"
        assert info["data_download_date"] == "2026-11-19"
        assert info["price_list_date"] == "2026-11-07"
        assert "outdated" in info["data_age_note"].lower()
        assert "indicative" in info["data_age_note"].lower()
        assert info["disclaimer"] == MANDATORY_DISCLAIMER
