import os
import re
import json
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from src.parsers.canonical import parse_composition, check_caution_drug, CanonicalProduct
from src.matching.brand_matcher import BrandMatcher, BrandMatchResult, BrandCandidate

MANDATORY_DISCLAIMER = "Information only, not medical advice. Ask your doctor or pharmacist before changing any medicine."

@dataclass
class BrandItemInfo:
    brand_name: str
    raw_composition: str
    pack_size_label: str
    pack_units: int
    price: float
    price_per_unit: float
    confidence: float
    dosage_form: Optional[str]
    release_type: str
    release_type_source: str = "assumed"
    release_type_note: Optional[str] = None
    canonical_key: Optional[str] = None

@dataclass
class GenericItemInfo:
    drug_code: str
    generic_name: str
    pack_label: str
    pack_units: int
    mrp: float
    price_per_unit: float
    therapeutic_group: str
    dosage_form: str
    release_type: str
    release_type_source: str = "assumed"
    release_type_note: Optional[str] = None
    is_price_ambiguous: bool = False
    price_status: str = "normal"
    price_list_date: str = "2026-11-07"
    price_list_date_source: str = "PDF creation date; official effective date not stated"

COMMONLY_MODIFIED_RELEASE_DRUGS = {
    # Proton Pump Inhibitors (PPIs)
    'pantoprazole', 'omeprazole', 'rabeprazole', 'esomeprazole', 'lansoprazole', 'ilaprazole',
    'pantoprazole sodium', 'rabeprazole sodium', 'omeprazole magnesium', 'esomeprazole magnesium',
    # NSAIDs & Analgesics
    'diclofenac', 'diclofenac sodium', 'diclofenac potassium',
    'aspirin', 'acetylsalicylic acid', 'tramadol', 'tramadol hydrochloride',
    # Antidiabetics
    'metformin', 'metformin hydrochloride',
    # Calcium Channel Blockers
    'nifedipine', 'diltiazem', 'diltiazem hydrochloride'
}

def is_commonly_modified_release(salts: List[Any]) -> bool:
    for salt_entry in salts:
        salt_name = salt_entry[0] if isinstance(salt_entry, (list, tuple)) else str(salt_entry)
        s_lower = salt_name.lower().strip()
        if s_lower in COMMONLY_MODIFIED_RELEASE_DRUGS:
            return True
        for drug in COMMONLY_MODIFIED_RELEASE_DRUGS:
            if re.search(r'\b' + re.escape(drug) + r'\b', s_lower):
                return True
    return False

@dataclass
class MatchItemResult:
    query: str
    match_type: str  # 'exact' | 'none' | 'uncertain' | 'unsupported'
    brand: Optional[Dict[str, Any]]
    generic: Optional[Dict[str, Any]]
    alternatives: List[Dict[str, Any]]
    saving_per_unit: Optional[float]
    saving_percent: Optional[float]
    has_caution: bool
    caution_flags: List[Dict[str, Any]]
    caution_message: Optional[str]
    candidates: List[Dict[str, Any]]
    reason: Optional[str]
    disclaimer: str = MANDATORY_DISCLAIMER

@dataclass
class PrescriptionSummary:
    total_items: int
    exact_matches_count: int
    uncertain_count: int
    no_match_count: int
    unsupported_count: int
    days_of_use: Optional[int]
    total_brand_cost: float
    total_generic_cost: float
    total_saving: float
    overall_saving_percent: float
    caution_items_count: int
    items: List[Dict[str, Any]]
    price_list_date: str
    disclaimer: str = MANDATORY_DISCLAIMER

class PillTwinEngine:
    """
    Core PillTwin Matching Engine.
    Executes Rule 1 (Strict Exact Match on salts, strengths, form, ER/IR),
    Rule 2 (Calculated savings from data with price_list_date),
    Rule 3 (Abstention below calibrated confidence threshold),
    Rule 5 (Doctor supervision flag on caution drugs with mandatory disclaimer).
    """
    def __init__(
        self,
        brand_parquet_path: str = "data/processed/brand_clean.parquet",
        formulary_json_path: str = "data/processed/formulary_index.json",
        calibration_json_path: str = "data/processed/matcher_calibration.json",
        caution_config_path: str = "config/caution_drugs.yaml",
        abstention_threshold: Optional[float] = None
    ):
        self.brand_matcher = BrandMatcher(
            brand_parquet_path=brand_parquet_path,
            calibration_json_path=calibration_json_path,
            abstention_threshold=abstention_threshold
        )
        
        if not os.path.exists(formulary_json_path):
            raise FileNotFoundError(f"Formulary index not found at {formulary_json_path}. Run make build first.")

        with open(formulary_json_path, "r", encoding="utf-8") as f:
            self.formulary: Dict[str, List[Dict[str, Any]]] = json.load(f)

        self.caution_config = {}
        if os.path.exists(caution_config_path):
            with open(caution_config_path, "r", encoding="utf-8") as f:
                self.caution_config = yaml.safe_load(f) or {}

        self.price_list_export_date = "2026-11-07"
        self.price_list_date_source = "PDF creation date; official effective date not stated"
        self.data_download_date = "2026-11-19"
        self.price_list_date = "2026-11-07"
        self.data_age_note = (
            "Brand prices are from a historical snapshot (commit d584adf) and may be outdated. "
            "Generic prices reflect the PMBJP price list exported on 2026-11-07. "
            "All savings are indicative information, not real-time quotes or medical advice."
        )

    def get_data_info(self) -> Dict[str, Any]:
        """Returns API data metadata, separate dates, and data age notice."""
        return {
            "price_list_export_date": self.price_list_export_date,
            "price_list_date_source": self.price_list_date_source,
            "data_download_date": self.data_download_date,
            "price_list_date": self.price_list_date,
            "data_age_note": self.data_age_note,
            "scope": "oral solid tablets and capsules only",
            "disclaimer": MANDATORY_DISCLAIMER
        }

    def match_item(
        self,
        query: str,
        confirmed_brand: Optional[str] = None,
        units_needed: Optional[int] = None
    ) -> MatchItemResult:
        """
        Matches a single query (or confirmed brand name) to its exact Jan Aushadhi generic twin.
        """
        # If user explicitly confirmed a brand name, look it up directly; otherwise use fuzzy matcher
        query_text = (confirmed_brand or query).strip()
        if not query_text:
            return MatchItemResult(
                query=query,
                match_type="uncertain",
                brand=None,
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=False,
                caution_flags=[],
                caution_message=None,
                candidates=[],
                reason="Query is empty. Please enter or confirm a medicine name."
            )

        # Check if the query itself specifies a non-solid oral formulation (Scope v1: tablets & capsules only)
        for pat in [r'\bsyrup\b', r'\bsuspension\b', r'\binjection\b', r'\binj\b', r'\bointment\b', r'\bgel\b', r'\bcream\b', r'\bdrops?\b', r'\bspray\b', r'\binhaler\b']:
            if re.search(pat, query_text, flags=re.I):
                if not re.search(r'\b(tablets?|capsules?)\b', query_text, flags=re.I):
                    return MatchItemResult(
                        query=query,
                        match_type="unsupported",
                        brand=None,
                        generic=None,
                        alternatives=[],
                        saving_per_unit=None,
                        saving_percent=None,
                        has_caution=False,
                        caution_flags=[],
                        caution_message=None,
                        candidates=[],
                        reason=f"Formulation matched pattern '{pat}'. Scope v1 covers oral solid tablets and capsules only. Other forms return 'Not supported yet'."
                    )

        match_res: BrandMatchResult = self.brand_matcher.find_matches(query_text, top_k=5)

        # 1. Check Abstention (Rule 3)
        if not match_res.is_confident and not confirmed_brand:
            candidate_dicts = [
                {
                    'brand_name': c.brand_name,
                    'similarity': c.similarity,
                    'calibrated_confidence': c.calibrated_confidence,
                    'raw_composition': c.raw_composition
                }
                for c in match_res.candidates
            ]
            return MatchItemResult(
                query=query,
                match_type="uncertain",
                brand=None,
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=False,
                caution_flags=[],
                caution_message=None,
                candidates=candidate_dicts,
                reason=match_res.abstain_reason or "Not sure. Please verify the name or ask a pharmacist."
            )

        top_cand = match_res.top_candidate
        if not top_cand:
            return MatchItemResult(
                query=query,
                match_type="none",
                brand=None,
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=False,
                caution_flags=[],
                caution_message=None,
                candidates=[],
                reason="Medicine not found in catalog."
            )

        # Retrieve full brand metadata
        bmeta = self.brand_matcher.brand_metadata.get(top_cand.brand_name.lower(), {})
        dosage_form = bmeta.get('dosage_form')
        release_type = bmeta.get('release_type', 'IR')
        release_type_source = bmeta.get('release_type_source', 'assumed')
        release_type_note = bmeta.get('release_type_note') or ("assumed immediate-release, not stated in source" if release_type == 'IR' else None)
        canonical_key = bmeta.get('canonical_key')
        raw_comp = bmeta.get('raw_composition', '')
        b_ppu = bmeta.get('price_per_unit', 0.0)
        b_pack = bmeta.get('pack_units', 10)
        b_price = bmeta.get('price', 0.0)

        # 2. Check Supported Dosage Form (Scope v1: Oral solids only)
        if not (dosage_form and (dosage_form.startswith('tablet') or dosage_form.startswith('capsule'))):
            return MatchItemResult(
                query=query,
                match_type="unsupported",
                brand={
                    'name': top_cand.brand_name,
                    'composition': raw_comp,
                    'dosage_form': dosage_form or 'unknown',
                    'release_type': release_type,
                    'release_type_source': release_type_source,
                    'release_type_note': release_type_note,
                    'pack_units': b_pack,
                    'price': b_price,
                    'price_per_unit': b_ppu,
                    'confidence': top_cand.calibrated_confidence
                },
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=False,
                caution_flags=[],
                caution_message=None,
                candidates=[],
                reason=f"Formulation '{dosage_form}' is not supported yet. Scope v1 covers oral solid tablets and capsules only."
            )

        # 3. Check Caution Drugs (Rule 5)
        parsed_comp = parse_composition(raw_comp, form_hint=dosage_form or "tablet")
        caution_flags = check_caution_drug(parsed_comp.salts, self.caution_config)
        has_caution = len(caution_flags) > 0
        caution_message = None
        if has_caution:
            caution_message = (
                "NEEDS PHARMACIST REVIEW: This medicine has a narrow therapeutic index or requires "
                "doctor supervision. Do not change brands without consulting your prescribing doctor or pharmacist."
            )

        brand_dict = {
            'name': top_cand.brand_name,
            'composition': raw_comp,
            'pack': bmeta.get('pack_size_label', f"{b_pack} units"),
            'pack_units': b_pack,
            'price': b_price,
            'price_per_unit': b_ppu,
            'dosage_form': dosage_form,
            'release_type': release_type,
            'release_type_source': release_type_source,
            'release_type_note': release_type_note,
            'canonical_key': canonical_key,
            'confidence': top_cand.calibrated_confidence
        }

        # 4. Check Commonly DR/ER Drugs with unstated release
        if is_commonly_modified_release(parsed_comp.salts) and release_type_source == "assumed":
            return MatchItemResult(
                query=query,
                match_type="uncertain",
                brand=brand_dict,
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=has_caution,
                caution_flags=caution_flags,
                caution_message=caution_message,
                candidates=[],
                reason="uncertain: release unknown (drug is commonly formulated as delayed-release/enteric-coated or extended-release; verify release type on strip or consult pharmacist)"
            )

        # 5. Exact Generic Matching (Rule 1: identical canonical key)
        if not canonical_key or canonical_key not in self.formulary:
            reason = "No Jan Aushadhi generic found with the exact same salts, strengths, dosage form, and release type."
            if canonical_key:
                brand_salts = canonical_key.split('|')[0]
                matching_salts = [k for k in self.formulary if k.startswith(brand_salts)]
                if not matching_salts:
                    reason = "No exact match found: salt differs (unknown or non-whitelisted salt form, or salt not in Jan Aushadhi catalog)."
                else:
                    reason = f"No exact match found with identical dosage form and release type (available forms: {', '.join(matching_salts[:3])})."

            return MatchItemResult(
                query=query,
                match_type="none",
                brand=brand_dict,
                generic=None,
                alternatives=[],
                saving_per_unit=None,
                saving_percent=None,
                has_caution=has_caution,
                caution_flags=caution_flags,
                caution_message=caution_message,
                candidates=[],
                reason=reason
            )

        # Exact match found!
        generic_options = self.formulary[canonical_key]
        primary_gen = generic_options[0]
        alt_generics = generic_options[1:] if len(generic_options) > 1 else []

        gen_ppu = float(primary_gen['price_per_unit'])
        gen_mrp = float(primary_gen['mrp'])
        gen_pack = int(primary_gen['pack_units'])

        # Per-unit price maths (Rule 2)
        saving_per_unit = round(b_ppu - gen_ppu, 4)
        if b_ppu > 0.0:
            saving_percent = round((saving_per_unit / b_ppu) * 100.0, 2)
        else:
            saving_percent = 0.0

        gen_release_type = primary_gen['release_type']
        gen_release_source = primary_gen.get('release_type_source', 'assumed')
        gen_release_note = primary_gen.get('release_type_note') or ("assumed immediate-release, not stated in source" if gen_release_type == 'IR' else None)
        is_ambiguous = primary_gen.get('is_price_ambiguous', len(generic_options) > 1)
        price_status = primary_gen.get('price_status', 'price ambiguous' if len(generic_options) > 1 else 'normal')

        generic_dict = {
            'code': primary_gen['drug_code'],
            'name': primary_gen['generic_name'],
            'pack': primary_gen['unit_size'],
            'pack_units': gen_pack,
            'mrp': gen_mrp,
            'price_per_unit': gen_ppu,
            'therapeutic_group': primary_gen['therapeutic_group'],
            'dosage_form': primary_gen['dosage_form'],
            'release_type': gen_release_type,
            'release_type_source': gen_release_source,
            'release_type_note': gen_release_note,
            'is_price_ambiguous': is_ambiguous,
            'price_status': price_status,
            'price_list_date': primary_gen.get('price_list_date', self.price_list_date),
            'price_list_date_source': self.price_list_date_source
        }

        # Where release type is assumed on either side, never show plain "exact".
        # Return "match on assumed release; confirm on strip".
        if release_type_source == "assumed" or gen_release_source == "assumed":
            match_type = "match on assumed release; confirm on strip"
        else:
            match_type = "exact"

        return MatchItemResult(
            query=query,
            match_type=match_type,
            brand=brand_dict,
            generic=generic_dict,
            alternatives=alt_generics,
            saving_per_unit=saving_per_unit,
            saving_percent=saving_percent,
            has_caution=has_caution,
            caution_flags=caution_flags,
            caution_message=caution_message,
            candidates=[],
            reason=None
        )

    def match_prescription(
        self,
        items: List[Dict[str, Any]] | List[str],
        days_of_use: Optional[int] = 30
    ) -> PrescriptionSummary:
        """
        Matches a multi-item prescription and computes aggregated financial totals.
        """
        results: List[MatchItemResult] = []
        total_brand_cost = 0.0
        total_generic_cost = 0.0
        exact_count = 0
        uncertain_count = 0
        none_count = 0
        unsupported_count = 0
        caution_count = 0

        for item in items:
            if isinstance(item, dict):
                q = item.get("name") or item.get("query", "")
                conf_name = item.get("confirmed_brand")
                units = item.get("units_needed")
            else:
                q = str(item)
                conf_name = None
                units = None

            res = self.match_item(query=q, confirmed_brand=conf_name, units_needed=units)
            results.append(res)

            if res.match_type in ("exact", "match on assumed release; confirm on strip"):
                exact_count += 1
                if res.has_caution:
                    caution_count += 1
                
                # Compute cost for course
                b_ppu = res.brand['price_per_unit'] if res.brand else 0.0
                g_ppu = res.generic['price_per_unit'] if res.generic else 0.0
                units_for_item = units or (days_of_use * 1 if days_of_use else 30)

                total_brand_cost += (b_ppu * units_for_item)
                total_generic_cost += (g_ppu * units_for_item)

            elif res.match_type == "uncertain":
                uncertain_count += 1
            elif res.match_type == "unsupported":
                unsupported_count += 1
            else:
                none_count += 1

        total_saving = round(total_brand_cost - total_generic_cost, 2)
        total_brand_cost = round(total_brand_cost, 2)
        total_generic_cost = round(total_generic_cost, 2)

        if total_brand_cost > 0:
            overall_pct = round((total_saving / total_brand_cost) * 100.0, 2)
        else:
            overall_pct = 0.0

        item_dicts = []
        for r in results:
            item_dicts.append({
                'query': r.query,
                'match_type': r.match_type,
                'brand': r.brand,
                'generic': r.generic,
                'saving_per_unit': r.saving_per_unit,
                'saving_percent': r.saving_percent,
                'has_caution': r.has_caution,
                'caution_flags': r.caution_flags,
                'caution_message': r.caution_message,
                'candidates': r.candidates,
                'reason': r.reason
            })

        return PrescriptionSummary(
            total_items=len(items),
            exact_matches_count=exact_count,
            uncertain_count=uncertain_count,
            no_match_count=none_count,
            unsupported_count=unsupported_count,
            days_of_use=days_of_use,
            total_brand_cost=total_brand_cost,
            total_generic_cost=total_generic_cost,
            total_saving=total_saving,
            overall_saving_percent=overall_pct,
            caution_items_count=caution_count,
            items=item_dicts,
            price_list_date=self.price_list_date
        )
