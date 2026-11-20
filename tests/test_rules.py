import pytest
import yaml
from src.parsers.canonical import parse_composition, check_caution_drug

@pytest.fixture
def caution_config():
    with open('config/caution_drugs.yaml', 'r') as f:
        return yaml.safe_load(f)

class TestRule1ExactMatchEnforcement:
    """
    NON-NEGOTIABLE RULE 1:
    'Exact match' ONLY if:
    1. Normalised salt set is identical
    2. Every strength with units is identical
    3. Dosage form (tablet vs capsule) is identical
    4. Release type (immediate vs extended/sustained/delayed) is identical
    
    Unit tests proving strength mismatch, missing/extra salt, form or ER/IR mismatch
    NEVER produce an exact match.
    """

    def test_strength_mismatch_never_exact_matches(self):
        # Paracetamol 500mg vs Paracetamol 650mg
        p1 = parse_composition("Paracetamol (500mg)", form_hint="tablet")
        p2 = parse_composition("Paracetamol (650mg)", form_hint="tablet")
        assert p1.canonical_key is not None
        assert p2.canonical_key is not None
        assert p1.canonical_key != p2.canonical_key, "500mg and 650mg must never match"

        # Telmisartan 40mg vs Telmisartan 80mg
        t40 = parse_composition("Telmisartan 40mg", form_hint="tablet")
        t80 = parse_composition("Telmisartan 80mg", form_hint="tablet")
        assert t40.canonical_key != t80.canonical_key

        # Metformin 500mg vs Metformin 1000mg
        m500 = parse_composition("Metformin 500mg", form_hint="tablet")
        m1000 = parse_composition("Metformin 1000mg", form_hint="tablet")
        assert m500.canonical_key != m1000.canonical_key

    def test_missing_or_extra_salt_never_exact_matches(self):
        # Monotherapy vs Fixed-dose combination
        mono = parse_composition("Amoxycillin (500mg)", form_hint="tablet")
        combo = parse_composition("Amoxycillin (500mg) + Clavulanic Acid (125mg)", form_hint="tablet")
        assert mono.canonical_key is not None
        assert combo.canonical_key is not None
        assert mono.canonical_key != combo.canonical_key, "Single salt must never match multi-salt combo"

        # Paracetamol alone vs Paracetamol + Caffeine
        pcm = parse_composition("Paracetamol 500mg", form_hint="tablet")
        pcm_caf = parse_composition("Paracetamol 500mg + Caffeine 50mg", form_hint="tablet")
        assert pcm.canonical_key != pcm_caf.canonical_key

        # Triple combo vs Double combo
        double_combo = parse_composition("Aceclofenac 100mg + Paracetamol 325mg", form_hint="tablet")
        triple_combo = parse_composition("Aceclofenac 100mg + Paracetamol 325mg + Serratiopeptidase 15mg", form_hint="tablet")
        assert double_combo.canonical_key != triple_combo.canonical_key

    def test_dosage_form_mismatch_never_exact_matches(self):
        # Tablet vs Capsule with identical salt and strength
        tab = parse_composition("Omeprazole 20mg", form_hint="strip of 10 tablets")
        cap = parse_composition("Omeprazole 20mg", form_hint="strip of 10 capsules")
        assert tab.dosage_form == "tablet"
        assert cap.dosage_form == "capsule"
        assert tab.canonical_key != cap.canonical_key, "Tablet and Capsule must never match"

        # Amoxicillin 500mg tablet vs Amoxicillin 500mg capsule
        amox_tab = parse_composition("Amoxycillin 500mg", form_hint="tablets")
        amox_cap = parse_composition("Amoxycillin 500mg", form_hint="capsules")
        assert amox_tab.canonical_key != amox_cap.canonical_key

    def test_release_type_mismatch_never_exact_matches(self):
        # Immediate release (IR) vs Prolonged/Extended release (ER/PR)
        ir = parse_composition("Metformin 500mg", form_hint="tablets", name_hint="Metformin 500")
        er = parse_composition("Metformin 500mg", form_hint="tablets", name_hint="Metformin 500 PR Prolonged Release")
        assert ir.release_type == "IR"
        assert er.release_type == "ER"
        assert ir.canonical_key != er.canonical_key, "IR and ER/PR formulations must never match"

        # Gastro-resistant / Enteric coated is 'DR', distinct from 'IR' and 'ER'
        diclo_ir = parse_composition("Diclofenac Sodium 50mg", form_hint="tablets")
        diclo_dr = parse_composition("Diclofenac Gastro-Resistant Tablets IP 50mg", form_hint="tablets")
        diclo_er = parse_composition("Diclofenac Sodium Prolonged Release Tablets IP 100 mg", form_hint="tablets")
        assert diclo_ir.release_type == "IR"
        assert diclo_dr.release_type == "DR"
        assert diclo_er.release_type == "ER"
        assert diclo_ir.canonical_key != diclo_dr.canonical_key, "IR and DR must never match"
        assert diclo_dr.canonical_key != diclo_er.canonical_key, "DR and ER must never match"
        assert diclo_ir.canonical_key != diclo_er.canonical_key, "IR and ER must never match"

        # Enteric-coated Aspirin is DR
        asp_dr = parse_composition("Aspirin Enteric Coated Tablets IP 75mg", form_hint="tablets")
        assert asp_dr.release_type == "DR"
        assert asp_dr.release_type_source == "stated"

        # Delayed-release Sulfasalazine is DR
        sulfa_dr = parse_composition("Sulfasalazine Delayed Release Tablets 500mg", form_hint="tablets")
        assert sulfa_dr.release_type == "DR"
        assert sulfa_dr.release_type_source == "stated"

    def test_release_type_source_and_assumed_ir_note(self):
        # Unstated IR defaults to assumed with mandatory notice
        ir_assumed = parse_composition("Paracetamol 650mg", form_hint="tablet")
        assert ir_assumed.release_type == "IR"
        assert ir_assumed.release_type_source == "assumed"
        assert ir_assumed.release_type_note == "assumed immediate-release, not stated in source"

        # Explicitly stated IR
        ir_stated = parse_composition("Paracetamol Immediate-Release Tablets 500mg", form_hint="tablet")
        assert ir_stated.release_type == "IR"
        assert ir_stated.release_type_source == "stated"
        assert ir_stated.release_type_note is None

        # ER is stated
        er_item = parse_composition("Metformin Sustained Release Tablets 500mg", form_hint="tablet")
        assert er_item.release_type == "ER"
        assert er_item.release_type_source == "stated"
        assert er_item.release_type_note is None

    def test_identical_composition_matches_regardless_of_order_or_spelling(self):
        # Permuted order: (A + B) vs (B + A)
        p1 = parse_composition("Amoxycillin (500mg) + Clavulanic Acid (125mg)", form_hint="tablet")
        p2 = parse_composition("Clavulanic Acid (125mg) + Amoxicillin (500mg)", form_hint="tablet")
        assert p1.canonical_key == p2.canonical_key, "Order of salts in input must not affect canonical key"

        # US vs UK spelling: Amoxycillin vs Amoxicillin
        uk = parse_composition("Amoxycillin 500mg", form_hint="tablet")
        us = parse_composition("Amoxicillin 500mg", form_hint="tablet")
        assert uk.canonical_key == us.canonical_key

        # Gram to Milligram normalization: 1g == 1000mg
        g_item = parse_composition("Amoxicillin 1g", form_hint="tablet")
        mg_item = parse_composition("Amoxicillin 1000mg", form_hint="tablet")
        assert g_item.canonical_key == mg_item.canonical_key

    def test_non_solid_oral_forms_rejected(self):
        syrup = parse_composition("Paracetamol Paediatric Oral Suspension IP 125 mg per 5 ml", form_hint="bottle of 60 ml syrup")
        assert not syrup.is_solid_oral
        assert syrup.canonical_key is None

        injection = parse_composition("Diclofenac Sodium Injection 25mg/ml", form_hint="vial of 3 ml")
        assert not injection.is_solid_oral
        assert injection.canonical_key is None

        ointment = parse_composition("Diclofenac Gel 1.16%", form_hint="tube of 30 gm")
        assert not ointment.is_solid_oral
        assert ointment.canonical_key is None

class TestCautionDrugsSupervision:
    """
    RULE 5: Doctor supervision required on caution drugs list.
    """
    def test_caution_drugs_flagged(self, caution_config):
        # Levothyroxine
        lt = parse_composition("Levothyroxine Sodium 50mcg", form_hint="tablet")
        flags = check_caution_drug(lt.salts, caution_config)
        assert len(flags) > 0
        assert flags[0]['id'] == 'levothyroxine'

        # Warfarin
        wf = parse_composition("Warfarin Sodium 5mg", form_hint="tablet")
        flags = check_caution_drug(wf.salts, caution_config)
        assert len(flags) > 0
        assert flags[0]['id'] == 'warfarin'

        # Antiepileptics (Phenytoin, Carbamazepine, Sodium Valproate)
        ph = parse_composition("Phenytoin Sodium 100mg", form_hint="tablet")
        assert len(check_caution_drug(ph.salts, caution_config)) > 0

        cb = parse_composition("Carbamazepine 200mg", form_hint="tablet")
        assert len(check_caution_drug(cb.salts, caution_config)) > 0

        # Non-caution drug (Paracetamol)
        pcm = parse_composition("Paracetamol 650mg", form_hint="tablet")
        assert len(check_caution_drug(pcm.salts, caution_config)) == 0

class TestPharmacologicalSaltPairDistinctions:
    """
    Ensures salt forms that imply distinct pharmacokinetics, release profiles,
    or clinical indications NEVER match.
    """
    def test_metoprolol_succinate_vs_tartrate_never_match(self):
        # Metoprolol Succinate (ER once-daily) vs Metoprolol Tartrate (IR multiple times daily)
        succ = parse_composition("Metoprolol Succinate 50mg", form_hint="tablet")
        tart = parse_composition("Metoprolol Tartrate 50mg", form_hint="tablet")
        assert succ.canonical_key != tart.canonical_key, "Metoprolol Succinate and Tartrate must NEVER exact match"

    def test_divalproex_vs_sodium_valproate_never_match(self):
        # Divalproex sodium coordination compound vs Sodium Valproate
        div = parse_composition("Divalproex Sodium 500mg", form_hint="tablet")
        val = parse_composition("Sodium Valproate 500mg", form_hint="tablet")
        assert div.canonical_key != val.canonical_key, "Divalproex and Sodium Valproate must NEVER exact match"

    def test_hydroxyzine_pamoate_vs_hydrochloride_never_match(self):
        # Hydroxyzine Pamoate vs Hydroxyzine Hydrochloride
        pam = parse_composition("Hydroxyzine Pamoate 25mg", form_hint="capsule")
        hcl = parse_composition("Hydroxyzine Hydrochloride 25mg", form_hint="tablet")
        assert pam.canonical_key != hcl.canonical_key

    def test_lamotrigine_dispersible_vs_standard_never_match(self):
        # Lamotrigine Standard (Code 931) vs Lamotrigine Dispersible (Code 1448)
        lam_std = parse_composition("Lamotrigine Tablets 100mg", form_hint="tablet", name_hint="Lamotrigine Tablets 100mg")
        lam_dt = parse_composition("Lamotrigine Dispersible Tablets IP 100mg", form_hint="tablet", name_hint="Lamotrigine Dispersible Tablets IP 100mg")
        assert lam_std.canonical_key != lam_dt.canonical_key, "Standard and Dispersible tablets must NEVER share canonical key"
        assert lam_std.dosage_form == "tablet"
        assert lam_dt.dosage_form == "tablet_dispersible"
        assert lam_std.canonical_key == "lamotrigine:100mg|tablet|IR"
        assert lam_dt.canonical_key == "lamotrigine:100mg|tablet_dispersible|IR"

    def test_acetylcysteine_effervescent_vs_standard_never_match(self):
        # Acetylcysteine Standard (Code 539) vs Acetylcysteine Effervescent (Code 2225)
        ac_std = parse_composition("Acetylcysteine Tablets 600 mg", form_hint="tablet", name_hint="Acetylcysteine Tablets 600 mg")
        ac_eff = parse_composition("Acetylcysteine Effervescent Tablets 600mg", form_hint="tablet", name_hint="Acetylcysteine Effervescent Tablets 600mg")
        assert ac_std.canonical_key != ac_eff.canonical_key, "Standard and Effervescent tablets must NEVER share canonical key"
        assert ac_std.dosage_form == "tablet"
        assert ac_eff.dosage_form == "tablet_effervescent"
        assert ac_std.canonical_key == "acetylcysteine:600mg|tablet|IR"
        assert ac_eff.canonical_key == "acetylcysteine:600mg|tablet_effervescent|IR"

    def test_aciclovir_dispersible_vs_standard_never_match(self):
        # Aciclovir Standard (Code 29) vs Dispersible (Code 1496)
        acv_std = parse_composition("Aciclovir Tablets IP 400 mg", form_hint="tablet", name_hint="Aciclovir Tablets IP 400 mg")
        acv_dt = parse_composition("Aciclovir Dispersible Tablets IP 400 mg", form_hint="tablet", name_hint="Aciclovir Dispersible Tablets IP 400 mg")
        assert acv_std.canonical_key != acv_dt.canonical_key
        assert acv_std.canonical_key == "aciclovir:400mg|tablet|IR"
        assert acv_dt.canonical_key == "aciclovir:400mg|tablet_dispersible|IR"

    def test_ferrous_sulphate_vs_fumarate_never_match(self):
        # Ferrous Sulphate vs Ferrous Fumarate (different elemental iron % and salts)
        fe_sulf = parse_composition("Ferrous Sulphate 100mg", form_hint="tablet")
        fe_fum = parse_composition("Ferrous Fumarate 100mg", form_hint="tablet")
        assert fe_sulf.canonical_key != fe_fum.canonical_key, "Ferrous Sulphate and Fumarate must NEVER exact match"
        assert "ferrous sulphate" in fe_sulf.canonical_key
        assert "ferrous fumarate" in fe_fum.canonical_key

    def test_isosorbide_mononitrate_vs_dinitrate_never_match(self):
        # Isosorbide Mononitrate vs Isosorbide Dinitrate (whole token matching, never substrings)
        mono = parse_composition("Isosorbide Mononitrate 30mg", form_hint="tablet")
        di = parse_composition("Isosorbide Dinitrate 30mg", form_hint="tablet")
        assert mono.canonical_key != di.canonical_key, "Isosorbide Mononitrate and Dinitrate must NEVER exact match"
        assert "isosorbide mononitrate" in mono.canonical_key
        assert "isosorbide dinitrate" in di.canonical_key

    def test_estradiol_valerate_vs_estradiol_never_match(self):
        # Estradiol Valerate vs Estradiol (valerate ester is distinct and NOT stripped by default)
        val = parse_composition("Estradiol Valerate 2mg", form_hint="tablet")
        est = parse_composition("Estradiol 2mg", form_hint="tablet")
        assert val.canonical_key != est.canonical_key, "Estradiol Valerate and Estradiol base must NEVER exact match"
        assert "estradiol valerate" in val.canonical_key
        assert "estradiol:2mg" in est.canonical_key

    def test_chloroquine_phosphate_vs_sulphate_never_match(self):
        # Chloroquine Phosphate vs Chloroquine Sulphate (distinct salt forms)
        phos = parse_composition("Chloroquine Phosphate 250mg", form_hint="tablet")
        sulf = parse_composition("Chloroquine Sulphate 250mg", form_hint="tablet")
        assert phos.canonical_key != sulf.canonical_key, "Chloroquine Phosphate and Sulphate must NEVER exact match"
        assert "chloroquine phosphate" in phos.canonical_key
        assert "chloroquine sulphate" in sulf.canonical_key

class TestPriceMathAndMultiSaltSplitting:
    """
    Tests exact per-unit price mathematics and multi-salt parsing integrity.
    """
    def test_per_unit_price_and_savings_math(self):
        # Scenario: Brand Augmentin 625 Duo: pack of 10 tablets at ₹223.42 -> ₹22.342/unit
        # Generic Amoxycillin 500mg + Potassium Clavulanate 125mg: pack of 6 tablets at ₹52.60 -> ₹8.7667/unit
        brand_mrp = 223.42
        brand_pack = 10
        brand_ppu = round(brand_mrp / brand_pack, 4)
        assert brand_ppu == 22.342

        gen_mrp = 52.60
        gen_pack = 6
        gen_ppu = round(gen_mrp / gen_pack, 4)
        assert gen_ppu == 8.7667

        saving_per_unit = round(brand_ppu - gen_ppu, 4)
        assert saving_per_unit == round(22.342 - 8.7667, 4)
        assert saving_per_unit == 13.5753

        saving_pct = round((saving_per_unit / brand_ppu) * 100, 2)
        assert saving_pct == 60.76  # Computed directly: (13.5753 / 22.342) * 100 = 60.76%

        # 30-day supply calculation (e.g. 2 tablets per day = 60 units)
        units_needed = 60
        brand_total = round(brand_ppu * units_needed, 2)
        gen_total = round(gen_ppu * units_needed, 2)
        total_saving = round(brand_total - gen_total, 2)
        assert brand_total == 1340.52
        assert gen_total == 526.00
        assert total_saving == 814.52

    def test_multi_salt_splitting_combinations(self):
        # 2-salt combination with '+'
        c2 = parse_composition("Amoxycillin (500mg) + Clavulanic Acid (125mg)", form_hint="tablet")
        assert len(c2.salts) == 2
        assert c2.salts[0] == ("amoxicillin", "500mg")
        assert c2.salts[1] == ("clavulanic acid", "125mg")

        # 3-salt combination with commas and 'and'
        c3 = parse_composition("Chlorzoxazone 500mg, Diclofenac 50mg and Paracetamol 325mg Tablets", form_hint="tablet")
        assert len(c3.salts) == 3
        salt_dict = dict(c3.salts)
        assert "chlorzoxazone" in salt_dict and salt_dict["chlorzoxazone"] == "500mg"
        assert "diclofenac" in salt_dict and salt_dict["diclofenac"] == "50mg"
        assert "paracetamol" in salt_dict and salt_dict["paracetamol"] == "325mg"

        # 4-salt combination
        c4 = parse_composition("Paracetamol 325mg + Phenylephrine 5mg + Chlorpheniramine 2mg + Caffeine 30mg", form_hint="tablet")
        assert len(c4.salts) == 4
        s4_dict = dict(c4.salts)
        assert s4_dict["paracetamol"] == "325mg"
        assert s4_dict["phenylephrine"] == "5mg"
        assert s4_dict["chlorpheniramine"] == "2mg"
        assert s4_dict["caffeine"] == "30mg"

    def test_diclofenac_sodium_vs_potassium_never_match(self):
        # Diclofenac Sodium vs Diclofenac Potassium (distinct pharmacokinetic dissolution profiles)
        sod = parse_composition("Diclofenac Sodium 50mg", form_hint="tablet")
        pot = parse_composition("Diclofenac Potassium 50mg", form_hint="tablet")
        assert sod.canonical_key != pot.canonical_key, "Diclofenac Sodium and Potassium must NEVER match"
        assert sod.canonical_key == "diclofenac sodium:50mg|tablet|IR"
        assert pot.canonical_key == "diclofenac potassium:50mg|tablet|IR"

    def test_rabeprazole_dr_domperidone_er_per_component_release(self):
        # Fixed-dose combination with distinct component release types
        combo = parse_composition(
            "Rabeprazole Sodium 20mg (Enteric Coated) + Domperidone 30mg (Sustained Release) Capsules",
            form_hint="capsule"
        )
        assert combo.canonical_key == "domperidone:30mg:ER;rabeprazole:20mg:DR|capsule"
        assert combo.release_type == "DR+ER"
        assert combo.component_releases is not None
        assert len(combo.component_releases) == 2
        
        comp_dict = {c['salt']: c for c in combo.component_releases}
        assert comp_dict['rabeprazole']['release_type'] == 'DR'
        assert comp_dict['rabeprazole']['release_type_source'] == 'stated'
        assert comp_dict['domperidone']['release_type'] == 'ER'
        assert comp_dict['domperidone']['release_type_source'] == 'stated'

