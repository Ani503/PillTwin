"""
scripts/evaluate.py
Evaluates PillTwin matching engine on:
1. 30 common Indian brands (eval/common_brands_truth.csv)
2. 20 negative controls (eval/negative_controls.csv)
3. 1-character typo robustness test on brand matcher
Computes Wilson 95% score confidence intervals, median & IQR savings.
Writes reports/metrics.json and reports/phase4_evaluation.md.
"""

import os
import re
import json
import math
import string
import random
import numpy as np
import pandas as pd

from src.matching.engine import PillTwinEngine
from src.parsers.canonical import SALT_EQUIVALENT_WHITELIST

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Computes Wilson score confidence interval for a binomial proportion.
    """
    if total == 0:
        return (0.0, 0.0)
    z = 1.959963984540054  # 95% confidence z-score
    p_hat = successes / total
    denominator = 1.0 + (z ** 2) / total
    centre = (p_hat + (z ** 2) / (2.0 * total)) / denominator
    margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z ** 2) / (4.0 * (total ** 2))))) / denominator
    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return (round(lower, 4), round(upper, 4))

def generate_1char_typos(word: str, count: int = 1, seed: int = 42) -> str:
    """Generates realistic 1-character typo variant (deletion, substitution, or insertion)."""
    rng = random.Random(seed)
    tokens = word.split()
    if not tokens:
        return word
    # Target primary brand root word
    target_idx = 0
    w = list(tokens[target_idx])
    if len(w) <= 3:
        target_idx = len(tokens) - 1
        w = list(tokens[target_idx])
    
    op = rng.choice(['sub', 'del', 'ins'])
    idx = rng.randint(1, len(w) - 2) if len(w) > 3 else 0
    if op == 'sub':
        w[idx] = rng.choice(string.ascii_lowercase)
    elif op == 'del' and len(w) > 3:
        w.pop(idx)
    else:
        w.insert(idx, rng.choice(string.ascii_lowercase))
        
    tokens[target_idx] = "".join(w)
    return " ".join(tokens)

def normalize_code(val) -> str | None:
    """Normalizes numeric drug codes so float 39.0 matches string 39."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() == 'nan' or s.lower() == 'none':
        return None
    try:
        return str(int(float(s)))
    except ValueError:
        return s

def run_evaluation():
    print("=== PILLTWIN PHASE 4: END-TO-END EVALUATION ===")
    
    engine = PillTwinEngine()
    
    # 1. Load Truth Datasets
    truth_path = "eval/common_brands_truth.csv"
    neg_path = "eval/negative_controls.csv"
    
    if not os.path.exists(truth_path) or not os.path.exists(neg_path):
        raise FileNotFoundError("Evaluation datasets not found in eval/. Run build scripts first.")
        
    truth_df = pd.read_csv(truth_path)
    neg_df = pd.read_csv(neg_path)
    
    print(f"[*] Loaded {len(truth_df)} common brand truth items.")
    print(f"[*] Loaded {len(neg_df)} negative controls.")

    # 2. Evaluate Common Brands
    common_results = []
    savings_per_tablet = []
    savings_percent_list = []
    
    total_truth_queries = len(truth_df)
    total_expected_matches = 0
    total_exact_matches_returned = 0
    correct_exact_matches = 0
    wrong_exact_matches = 0
    missed_matches = []
    abstentions_count = 0
    no_generic_expected_count = 0
    correct_no_match_count = 0

    for idx, row in truth_df.iterrows():
        brand_q = str(row['brand_name']).strip()
        exp_code = normalize_code(row['expected_pmbjp_code'])
        exp_status = str(row['expected_match_status']).strip()
        
        # Execute query through matching engine
        res = engine.match_item(brand_q)
        actual_code = normalize_code(res.generic['code']) if res.generic else None
        actual_match_type = res.match_type
        
        is_exact_match_type = actual_match_type in ["exact", "match on assumed release; confirm on strip"]
        
        if is_exact_match_type:
            total_exact_matches_returned += 1
            if exp_code and actual_code == exp_code:
                correct_exact_matches += 1
                match_classification = "CORRECT_EXACT_MATCH"
            else:
                wrong_exact_matches += 1
                match_classification = f"WRONG_EXACT_MATCH (Got {actual_code}, Exp {exp_code})"
        elif actual_match_type == "uncertain":
            abstentions_count += 1
            match_classification = "ABSTAINED_UNCERTAIN"
        elif actual_match_type in ["none", "unsupported"]:
            if exp_code is None:
                correct_no_match_count += 1
                match_classification = "CORRECT_NO_MATCH"
            else:
                match_classification = "MISSED_GENERIC_MATCH"
        else:
            match_classification = "OTHER"

        if exp_code:
            total_expected_matches += 1
            if not is_exact_match_type:
                missed_matches.append({
                    'brand_name': brand_q,
                    'expected_code': exp_code,
                    'expected_name': row.get('expected_pmbjp_name', ''),
                    'actual_match_type': actual_match_type,
                    'reason': res.reason or "No match returned"
                })
        else:
            no_generic_expected_count += 1

        # Price savings calculation
        saving_ppu = None
        saving_pct = None
        if is_exact_match_type and res.brand and res.generic:
            b_ppu = float(res.brand.get('price_per_unit', 0.0))
            g_ppu = float(res.generic.get('price_per_unit', 0.0))
            if b_ppu > 0:
                saving_ppu = round(b_ppu - g_ppu, 4)
                saving_pct = round((saving_ppu / b_ppu) * 100.0, 2)
                savings_per_tablet.append(saving_ppu)
                savings_percent_list.append(saving_pct)

        common_results.append({
            'index': idx + 1,
            'brand_name': brand_q,
            'composition': row.get('raw_composition', ''),
            'dosage_form': row.get('dosage_form', ''),
            'release_type': row.get('release_type', ''),
            'is_combination': bool(row.get('is_combination', False)),
            'is_modified_or_dt': bool(row.get('is_modified_or_dt', False)),
            'expected_code': exp_code,
            'actual_code': actual_code,
            'match_type': actual_match_type,
            'classification': match_classification,
            'saving_per_tablet': saving_ppu,
            'saving_percent': saving_pct,
            'reason': res.reason
        })

    # Coverage & Precision Calculations
    coverage_rate = correct_exact_matches / total_expected_matches if total_expected_matches > 0 else 0.0
    coverage_ci = wilson_score_interval(correct_exact_matches, total_expected_matches)

    wrong_exact_rate = wrong_exact_matches / total_exact_matches_returned if total_exact_matches_returned > 0 else 0.0
    wrong_exact_ci = wilson_score_interval(wrong_exact_matches, total_exact_matches_returned)

    exact_precision = correct_exact_matches / total_exact_matches_returned if total_exact_matches_returned > 0 else 1.0
    precision_ci = wilson_score_interval(correct_exact_matches, total_exact_matches_returned)

    abstention_rate = abstentions_count / total_truth_queries if total_truth_queries > 0 else 0.0
    abstention_ci = wilson_score_interval(abstentions_count, total_truth_queries)

    # Median & IQR of per-tablet savings
    if savings_per_tablet:
        savings_arr = np.array(savings_per_tablet)
        pct_arr = np.array(savings_percent_list)
        med_saving = float(np.median(savings_arr))
        q25_saving = float(np.percentile(savings_arr, 25))
        q75_saving = float(np.percentile(savings_arr, 75))
        iqr_saving = round(q75_saving - q25_saving, 4)

        med_pct = float(np.median(pct_arr))
        q25_pct = float(np.percentile(pct_arr, 25))
        q75_pct = float(np.percentile(pct_arr, 75))
        iqr_pct = round(q75_pct - q25_pct, 2)
    else:
        med_saving, q25_saving, q75_saving, iqr_saving = 0.0, 0.0, 0.0, 0.0
        med_pct, q25_pct, q75_pct, iqr_pct = 0.0, 0.0, 0.0, 0.0

    # 3. Evaluate Negative Controls
    neg_results = []
    neg_false_exact_matches = 0
    total_negative_controls = len(neg_df)

    for idx, row in neg_df.iterrows():
        q_text = str(row['query_text']).strip()
        res = engine.match_item(q_text)
        is_exact = res.match_type in ["exact", "match on assumed release; confirm on strip"]
        if is_exact:
            neg_false_exact_matches += 1
            status = "FAILED_FALSE_EXACT_MATCH"
        else:
            status = "PASSED_REJECTED"

        reason_text = str(row.get('intended_rejection_reason', ''))
        cat_text = reason_text.split(':')[0].strip() if ':' in reason_text else 'Negative Control'
        neg_results.append({
            'control_id': row.get('control_id', idx + 1),
            'query_text': q_text,
            'category': cat_text,
            'intended_rejection_reason': reason_text,
            'rule_enforced': row.get('rule_enforced', ''),
            'actual_match_type': res.match_type,
            'reason': res.reason,
            'status': status
        })

    neg_false_rate = neg_false_exact_matches / total_negative_controls if total_negative_controls > 0 else 0.0
    neg_false_ci = wilson_score_interval(neg_false_exact_matches, total_negative_controls)
    neg_rejection_rate = (total_negative_controls - neg_false_exact_matches) / total_negative_controls
    neg_rejection_ci = wilson_score_interval(total_negative_controls - neg_false_exact_matches, total_negative_controls)

    # 4. 1-Character Typo Robustness Test on Matcher
    typo_results = []
    typo_candidate_successes = 0
    typo_exact_matches_returned = 0
    total_typo_tests = len(truth_df)

    for idx, row in truth_df.iterrows():
        orig_name = str(row['brand_name']).strip()
        typo_query = generate_1char_typos(orig_name, seed=42 + idx)
        
        # Test brand matcher candidate retrieval
        bm_res = engine.brand_matcher.find_matches(typo_query, top_k=3)
        retrieved_candidates = [c.brand_name.lower() for c in bm_res.candidates]
        
        # Check if original brand was retrieved in top candidates (Rule 4 user confirmation list)
        cand_success = orig_name.lower() in retrieved_candidates
        if cand_success:
            typo_candidate_successes += 1

        # Test end-to-end match_item on unconfirmed typo query (Rule 3 precision-first abstention)
        res_typo = engine.match_item(typo_query)
        is_typo_exact = res_typo.match_type in ["exact", "match on assumed release; confirm on strip"]
        if is_typo_exact:
            typo_exact_matches_returned += 1

        top_cand_name = bm_res.candidates[0].brand_name if bm_res.candidates else "None"
        top_conf = bm_res.candidates[0].calibrated_confidence if bm_res.candidates else 0.0

        typo_results.append({
            'original_brand': orig_name,
            'typo_query': typo_query,
            'top_retrieved_brand': top_cand_name,
            'confidence': round(top_conf, 4),
            'in_top_3': cand_success,
            'match_type': res_typo.match_type
        })

    typo_candidate_rate = typo_candidate_successes / total_typo_tests if total_typo_tests > 0 else 0.0
    typo_candidate_ci = wilson_score_interval(typo_candidate_successes, total_typo_tests)

    typo_exact_rate = typo_exact_matches_returned / total_typo_tests if total_typo_tests > 0 else 0.0
    typo_exact_ci = wilson_score_interval(typo_exact_matches_returned, total_typo_tests)

    # 5. Compile Metrics JSON (Data-backed only)
    metrics_data = {
        "metadata": {
            "evaluation_date": "2026-11-20",
            "eval_sample_size": total_truth_queries,
            "truth_source": "agent-drafted from PMBJP list, not human-verified",
            "ocr_measured": False,
            "claim_of_verification": False,
            "brand_price_snapshot": "commit d584adf (~2 years old)",
            "pmbjp_price_list_date": "2026-11-07",
            "pmbjp_price_list_date_source": "PDF creation date; official effective date not stated"
        },
        "exact_match_precision": {
            "value": round(exact_precision, 4),
            "wrong_exact_matches": wrong_exact_matches,
            "total_exact_matches_returned": total_exact_matches_returned,
            "wilson_95_ci": [precision_ci[0], precision_ci[1]]
        },
        "coverage": {
            "value": round(coverage_rate, 4),
            "correct_exact_matches": correct_exact_matches,
            "total_expected_matches": total_expected_matches,
            "wilson_95_ci": [coverage_ci[0], coverage_ci[1]]
        },
        "abstentions": {
            "count": abstentions_count,
            "total_queries": total_truth_queries,
            "rate": round(abstention_rate, 4),
            "wilson_95_ci": [abstention_ci[0], abstention_ci[1]]
        },
        "negative_controls": {
            "total_controls": total_negative_controls,
            "false_exact_matches": neg_false_exact_matches,
            "false_exact_rate": round(neg_false_rate, 4),
            "wilson_95_ci": [neg_false_ci[0], neg_false_ci[1]],
            "rejection_rate": round(neg_rejection_rate, 4),
            "rejection_wilson_95_ci": [neg_rejection_ci[0], neg_rejection_ci[1]]
        },
        "per_tablet_savings": {
            "note": "indicative; brand prices about 2 years old",
            "matched_pairs_evaluated": len(savings_per_tablet),
            "median_inr": round(med_saving, 4),
            "q25_inr": round(q25_saving, 4),
            "q75_inr": round(q75_saving, 4),
            "iqr_inr": round(iqr_saving, 4),
            "median_percent": round(med_pct, 2),
            "q25_percent": round(q25_pct, 2),
            "q75_percent": round(q75_pct, 2),
            "iqr_percent": round(iqr_pct, 2)
        },
        "matcher_typo_robustness": {
            "note": "matcher typo robustness, NOT an OCR accuracy test",
            "candidate_retrieval_success_count": typo_candidate_successes,
            "total_tests": total_typo_tests,
            "candidate_retrieval_rate": round(typo_candidate_rate, 4),
            "candidate_retrieval_wilson_95_ci": [typo_candidate_ci[0], typo_candidate_ci[1]],
            "exact_matches_returned_on_unconfirmed_typos": typo_exact_matches_returned,
            "exact_match_rate_on_unconfirmed_typos": round(typo_exact_rate, 4),
            "exact_match_rate_wilson_95_ci": [typo_exact_ci[0], typo_exact_ci[1]]
        }
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print("[+] Saved reports/metrics.json")

    # 6. Build Detailed Evaluation Markdown Report
    report_md = f"""# PillTwin Phase 4 Evaluation Report

**Notice:** n=30, truth drafted by the agent and not human-verified. OCR accuracy not measured. No claim of verification.

**Generated on:** 2026-11-20  
**Price List Export Date:** 2026-11-07 (`price_list_date_source`: PDF creation date; official effective date not stated)  
**Brand Data Download Date:** 2026-11-19 (JuniorAlive/Indian-Medicine-Dataset, commit `d584adf`, ~2 years old; brand prices may be outdated and savings are indicative)  
**Evaluation Benchmark:** 30 common Indian brands (`eval/common_brands_truth.csv`) + 20 negative controls (`eval/negative_controls.csv`)  

---

## 1. Summary of Evaluation Metrics

| Metric | Raw Counts | Point Estimate | Wilson 95% Confidence Interval | Method / Note |
| :--- | :---: | :---: | :---: | :--- |
| **Wrong Exact Matches** | **{wrong_exact_matches} / {total_exact_matches_returned}** | **{wrong_exact_rate*100:.2f}%** | **[{wrong_exact_ci[0]*100:.2f}%, {wrong_exact_ci[1]*100:.2f}%]** | Wrong exact matches of total exact matches returned |
| **Exact Match Precision** | **{correct_exact_matches} / {total_exact_matches_returned}** | **{exact_precision*100:.2f}%** | **[{precision_ci[0]*100:.2f}%, {precision_ci[1]*100:.2f}%]** | Precision over returned exact matches |
| **Coverage** | **{correct_exact_matches} / {total_expected_matches}** | **{coverage_rate*100:.2f}%** | **[{coverage_ci[0]*100:.2f}%, {coverage_ci[1]*100:.2f}%]** | Valid exact matches found / generic-expected items |
| **Abstentions** | **{abstentions_count} / {total_truth_queries}** | **{abstention_rate*100:.2f}%** | **[{abstention_ci[0]*100:.2f}%, {abstention_ci[1]*100:.2f}%]** | Precision-first abstentions (below threshold or unstated release) |
| **Negative Control False Matches** | **{neg_false_exact_matches} / {total_negative_controls}** | **{neg_false_rate*100:.2f}%** | **[{neg_false_ci[0]*100:.2f}%, {neg_false_ci[1]*100:.2f}%]** | Must be 0% (Rule 1 & Scope v1 enforcement) |
| **Median Per-Tablet Saving** | **{len(savings_per_tablet)} pairs** | **₹{med_saving:.2f}** (IQR: ₹{iqr_saving:.2f}) | Q1: ₹{q25_saving:.2f}, Q3: ₹{q75_saving:.2f} | *indicative; brand prices about 2 years old* |
| **1-Char Typo Candidate Retrieval (Top-3)** | **{typo_candidate_successes} / {total_typo_tests}** | **{typo_candidate_rate*100:.2f}%** | **[{typo_candidate_ci[0]*100:.2f}%, {typo_candidate_ci[1]*100:.2f}%]** | *Candidate retrieval for user confirmation (Rule 4)* |
| **Exact Matches on Unconfirmed Typos** | **{typo_exact_matches_returned} / {total_typo_tests}** | **{typo_exact_rate*100:.2f}%** | **[{typo_exact_ci[0]*100:.2f}%, {typo_exact_ci[1]*100:.2f}%]** | *Direct exact match on typo query (Rule 3 abstention)* |

---

## 2. Common Brands Benchmark Evaluation (n=30)

Breakdown of all 30 common Indian brands evaluated against ground truth PMBJP generics:

| # | Brand Name | Dosage Form | Release | Expected Code | Actual Code | Match Type | Saving / Unit (₹) | Saving % | Result Status |
| :-: | :--- | :---: | :---: | :-: | :-: | :--- | :-: | :-: | :--- |
"""
    for r in common_results:
        s_ppu_str = f"₹{r['saving_per_tablet']:.2f}" if r['saving_per_tablet'] is not None else "-"
        s_pct_str = f"{r['saving_percent']:.1f}%" if r['saving_percent'] is not None else "-"
        exp_code_str = r['expected_code'] if r['expected_code'] else "None"
        act_code_str = r['actual_code'] if r['actual_code'] else "None"
        report_md += f"| {r['index']} | **{r['brand_name']}** | `{r['dosage_form']}` | `{r['release_type']}` | `{exp_code_str}` | `{act_code_str}` | `{r['match_type']}` | {s_ppu_str} | {s_pct_str} | **{r['classification']}** |\n"

    report_md += f"""
---

## 3. Detailed Analysis of Wrong, Missed, or Abstained Matches

### Total Missed Matches on Generic-Expected Items: {len(missed_matches)}
"""
    if not missed_matches:
        report_md += "- *None: All items expecting an exact generic match were successfully matched.*\n"
    else:
        for m in missed_matches:
            report_md += f"#### Brand: `{m['brand_name']}`\n"
            report_md += f"- **Expected PMBJP Generic:** Code `{m['expected_code']}` (`{m['expected_name']}`)\n"
            report_md += f"- **Actual Engine Output:** Match Type: `{m['actual_match_type']}`\n"
            report_md += f"- **Engine Decision Rationale:** {m['reason']}\n"
            if "Thyronorm" in m['brand_name']:
                report_md += f"  - *Root Cause Analysis:* Brand packaging raw composition was cataloged as plain `Thyroxine (100mcg)` without the sodium suffix, whereas PMBJP item 332 is `Thyroxine Sodium`. Under Rule 1 whitelist rules, un-whitelisted salt differences prevent exact match ('salt differs').\n"
            report_md += "\n"

    report_md += f"""---

## 4. Negative Controls Benchmark (n=20)

Every negative control represents an intentional failure mode (strength mismatch, salt distinction, release type difference, standard vs dispersible, unsupported formulation). All 20 items must be rejected:

| ID | Query Text | Category | Rule Enforced | Match Type | Status | Intended Rejection Reason |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
"""
    for nr in neg_results:
        report_md += f"| {nr['control_id']} | `{nr['query_text']}` | {nr['category']} | {nr['rule_enforced']} | `{nr['actual_match_type']}` | **{nr['status']}** | {nr['intended_rejection_reason']} |\n"

    report_md += f"""
---

## 5. Matcher 1-Character Typo Robustness Test (n=30)

*Label: matcher typo robustness, NOT an OCR accuracy test*  
Evaluated by injecting synthetic 1-character perturbations (deletions, substitutions, insertions) into the commercial brand names:

| Original Brand Name | Synthetic Typo Query | Top Retrieved Brand | Confidence | Retrieved in Top-3 |
| :--- | :--- | :--- | :---: | :---: |
"""
    for tr in typo_results:
        report_md += f"| `{tr['original_brand']}` | `{tr['typo_query']}` | `{tr['top_retrieved_brand']}` | **{tr['confidence']*100:.1f}%** | {'PASSED' if tr['in_top_3'] else 'MISSED'} |\n"

    report_md += f"""
- **Candidate Retrieval for User Confirmation (Rule 4):** **{typo_candidate_successes} / {total_typo_tests} ({typo_candidate_rate*100:.2f}%)** [Wilson 95% CI: {typo_candidate_ci[0]*100:.2f}% - {typo_candidate_ci[1]*100:.2f}%]
- **Exact Matches Returned on Unconfirmed Typos (Rule 3):** **{typo_exact_matches_returned} / {total_typo_tests} ({typo_exact_rate*100:.2f}%)** [Wilson 95% CI: {typo_exact_ci[0]*100:.2f}% - {typo_exact_ci[1]*100:.2f}%]

---
"""

    with open("reports/phase4_evaluation.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[+] Saved reports/phase4_evaluation.md ({len(report_md)} bytes)")

    # Return key data for printing
    return metrics_data, common_results, neg_results

if __name__ == "__main__":
    run_evaluation()
