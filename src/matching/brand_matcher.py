import os
import re
import json
import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer

@dataclass
class BrandCandidate:
    brand_name: str
    similarity: float
    calibrated_confidence: float
    canonical_key: Optional[str]
    raw_composition: Optional[str]
    price_per_unit: Optional[float]

@dataclass
class BrandMatchResult:
    query: str
    top_candidate: Optional[BrandCandidate]
    is_confident: bool
    calibrated_confidence: float
    candidates: List[BrandCandidate]
    abstain_reason: Optional[str] = None

class BrandMatcher:
    """
    Character n-gram TF-IDF Brand Matcher with calibrated confidence
    (Platt scaling fitted inside cross-validation), strength & modifier consistency
    checks, and precision-first abstention logic.
    """
    def __init__(
        self,
        brand_parquet_path: str = "data/processed/brand_clean.parquet",
        calibration_json_path: str = "data/processed/matcher_calibration.json",
        abstention_threshold: Optional[float] = None
    ):
        self.brand_parquet_path = brand_parquet_path
        self.calibration_json_path = calibration_json_path

        if not os.path.exists(brand_parquet_path):
            raise FileNotFoundError(f"Brand dataset not found at {brand_parquet_path}. Run make build first.")

        # Load brand catalog
        df_brands = pd.read_parquet(brand_parquet_path)
        
        # Calibration defaults
        self.intercept = -6.2696
        self.coef = 9.4038
        self.threshold = 0.75

        if os.path.exists(calibration_json_path):
            with open(calibration_json_path, "r", encoding="utf-8") as f:
                calib = json.load(f)
                self.intercept = float(calib.get("intercept", self.intercept))
                self.coef = float(calib.get("coef", self.coef))
                if abstention_threshold is not None:
                    self.threshold = abstention_threshold
                else:
                    self.threshold = float(calib.get("abstention_threshold", 0.75))
        elif abstention_threshold is not None:
            self.threshold = abstention_threshold

        # Build lookup table for brand metadata
        self.catalog_names: List[str] = []
        self.brand_metadata: Dict[str, Dict[str, Any]] = {}

        for row in df_brands.itertuples(index=False):
            bname = str(row.brand_name).strip()
            bname_lower = bname.lower()
            if not bname or bname_lower in self.brand_metadata:
                continue
            self.catalog_names.append(bname)
            self.brand_metadata[bname_lower] = {
                'brand_id': getattr(row, 'brand_id', 0),
                'brand_name': bname,
                'manufacturer': getattr(row, 'manufacturer', ''),
                'pack_size_label': getattr(row, 'pack_size_label', ''),
                'pack_units': int(row.pack_units) if pd.notnull(row.pack_units) else 10,
                'price': float(row.price) if pd.notnull(row.price) else 0.0,
                'price_per_unit': float(row.price_per_unit) if pd.notnull(row.price_per_unit) else 0.0,
                'raw_composition': getattr(row, 'raw_composition', ''),
                'dosage_form': getattr(row, 'dosage_form', None),
                'release_type': getattr(row, 'release_type', 'IR'),
                'release_type_source': getattr(row, 'release_type_source', 'assumed'),
                'release_type_note': getattr(row, 'release_type_note', None),
                'canonical_key': getattr(row, 'canonical_key', None),
                'has_caution': bool(getattr(row, 'has_caution', False)),
                'caution_json': getattr(row, 'caution_json', '[]')
            }

        del df_brands

        # Vectorize brand names using normalized representations for consistent comparison
        self.catalog_names_norm = [self._normalize_text(name) for name in self.catalog_names]
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(3, 5),
            min_df=2,
            dtype=np.float32
        )
        self.X_catalog = self.vectorizer.fit_transform(self.catalog_names_norm)
        self.X_catalog_T = self.X_catalog.T.tocsc()

    def calibrate_probability(self, raw_cosine_sim: float) -> float:
        """
        Computes calibrated probability via Platt scaling:
        P(correct | score) = 1 / (1 + exp(-(intercept + coef * score)))
        """
        sim = float(np.clip(raw_cosine_sim, 0.0, 1.0))
        logit = self.intercept + (self.coef * sim)
        if logit > 20.0:
            return 1.0
        elif logit < -20.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-logit))

    @staticmethod
    def _extract_numbers(s: str) -> set:
        nums = set()
        s_lower = s.lower()
        # Convert grams to mg representations (e.g. 1gm -> 1000)
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:g|gm)\b', s_lower):
            try:
                val = float(m.group(1)) * 1000.0
                nums.add(f"{int(val)}" if val.is_integer() else f"{val:g}")
            except ValueError:
                pass
        for n in re.findall(r'(\d+(?:\.\d+)?)', s_lower):
            nums.add(n)
        return nums

    @staticmethod
    def _normalize_text(s: str) -> str:
        t = s.lower()
        t = re.sub(r'[-_]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def find_matches(self, query: str, top_k: int = 5) -> BrandMatchResult:
        """
        Finds closest brand names using character n-gram cosine similarity,
        adjusts for strength and modifier consistency, computes calibrated confidence,
        and enforces precision-first abstention.
        """
        q_clean = query.strip()
        if not q_clean or len(q_clean) < 2:
            return BrandMatchResult(
                query=query,
                top_candidate=None,
                is_confident=False,
                calibrated_confidence=0.0,
                candidates=[],
                abstain_reason="Query is empty or too short."
            )

        q_norm = self._normalize_text(q_clean)
        q_nums = self._extract_numbers(q_norm)
        q_words = set(q_norm.split())

        # Significant combination and formulation modifiers
        key_modifiers = {'m', 'd', 'duo', 'plus', 'forte', 'sr', 'pr', 'er', 'dt', 'cr', 'xl', 'xr', 'mr'}
        q_mods = q_words & key_modifiers

        # Vectorize query and compute raw similarities
        q_vec = self.vectorizer.transform([q_norm])
        sims = q_vec.dot(self.X_catalog_T).toarray()[0]
        sims = np.clip(sims, 0.0, 1.0)

        # Retrieve top 40 candidates by raw n-gram similarity
        pool_size = min(40, len(self.catalog_names))
        top_pool_indices = np.argsort(sims)[::-1][:pool_size]

        scored_candidates = []
        for idx in top_pool_indices:
            raw_sim = float(sims[idx])
            if raw_sim <= 0.02:
                continue

            cand_name = self.catalog_names[idx]
            cand_norm = self._normalize_text(cand_name)
            cand_nums = self._extract_numbers(cand_norm)
            cand_words = set(cand_norm.split())
            cand_mods = cand_words & key_modifiers

            # 1. Strength number consistency
            strength_mismatch = False
            if q_nums:
                if not cand_nums:
                    strength_mismatch = True
                elif not (q_nums & cand_nums):
                    strength_mismatch = True

            # 2. Modifier consistency
            mod_mismatch = False
            if q_mods and not (q_mods & cand_mods):
                mod_mismatch = True
            elif not q_mods and cand_mods:
                mod_mismatch = True
            elif ('forte' in cand_mods and 'forte' not in q_mods) or ('plus' in cand_mods and 'plus' not in q_mods):
                mod_mismatch = True

            # 3. Stem compatibility check
            q_stem = q_norm.split()[0] if q_norm.split() else ''
            cand_stem = cand_norm.split()[0] if cand_norm.split() else ''
            stem_match = (q_stem == cand_stem) or (len(q_stem) >= 3 and len(cand_stem) >= 3 and q_stem[:3] == cand_stem[:3])

            # Apply domain-specific precision adjustments
            adj_sim = raw_sim
            if strength_mismatch:
                adj_sim -= 0.35 # severe penalty for conflicting strength number
            elif q_nums and (q_nums & cand_nums):
                adj_sim += 0.05 # reward matching strength number

            if mod_mismatch:
                adj_sim -= 0.20 # penalty for missing/extra combo modifier
            elif q_mods and (q_mods & cand_mods):
                adj_sim += 0.05

            if not stem_match:
                adj_sim -= 0.25 # penalty if first word doesn't match root stem

            adj_sim = float(np.clip(adj_sim, 0.0, 1.0))
            prob = self.calibrate_probability(adj_sim)

            meta = self.brand_metadata.get(cand_name.lower(), {})
            scored_candidates.append({
                'candidate': BrandCandidate(
                    brand_name=cand_name,
                    similarity=round(raw_sim, 4),
                    calibrated_confidence=round(prob, 4),
                    canonical_key=meta.get('canonical_key'),
                    raw_composition=meta.get('raw_composition'),
                    price_per_unit=meta.get('price_per_unit')
                ),
                'adj_sim': adj_sim,
                'strength_mismatch': strength_mismatch,
                'mod_mismatch': mod_mismatch
            })

        if not scored_candidates:
            return BrandMatchResult(
                query=query,
                top_candidate=None,
                is_confident=False,
                calibrated_confidence=0.0,
                candidates=[],
                abstain_reason="No plausible medicine brand found in catalog."
            )

        # Sort by adjusted similarity descending
        scored_candidates.sort(key=lambda x: x['adj_sim'], reverse=True)
        top_entry = scored_candidates[0]
        top_cand = top_entry['candidate']

        final_candidates = [item['candidate'] for item in scored_candidates[:top_k]]

        # Abstention evaluation
        is_confident = (
            top_cand.calibrated_confidence >= self.threshold
            and not top_entry['strength_mismatch']
            and not top_entry['mod_mismatch']
        )

        abstain_reason = None
        if not is_confident:
            if top_entry['strength_mismatch']:
                abstain_reason = "Possible strength mismatch between query and closest brand. Please confirm medicine name."
            elif top_entry['mod_mismatch']:
                abstain_reason = "Possible formulation or modifier difference. Please confirm medicine name."
            else:
                abstain_reason = (
                    f"Confidence ({top_cand.calibrated_confidence:.1%}) is below calibrated safety threshold "
                    f"({self.threshold:.1%}). Please verify the medicine name or ask a pharmacist."
                )

        return BrandMatchResult(
            query=query,
            top_candidate=top_cand,
            is_confident=is_confident,
            calibrated_confidence=top_cand.calibrated_confidence,
            candidates=final_candidates,
            abstain_reason=abstain_reason
        )
