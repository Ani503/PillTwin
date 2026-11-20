# PillTwin Phase 4 Evaluation Report

**Notice:** n=30, truth drafted by the agent and not human-verified. OCR accuracy not measured. No claim of verification.

**Generated on:** 2026-11-20  
**Price List Export Date:** 2026-11-07 (`price_list_date_source`: PDF creation date; official effective date not stated)  
**Brand Data Download Date:** 2026-11-19 (JuniorAlive/Indian-Medicine-Dataset, commit `d584adf`, ~2 years old; brand prices may be outdated and savings are indicative)  
**Evaluation Benchmark:** 30 common Indian brands (`eval/common_brands_truth.csv`) + 20 negative controls (`eval/negative_controls.csv`)  

---

## 1. Summary of Evaluation Metrics

| Metric | Raw Counts | Point Estimate | Wilson 95% Confidence Interval | Method / Note |
| :--- | :---: | :---: | :---: | :--- |
| **Wrong Exact Matches** | **0 / 23** | **0.00%** | **[0.00%, 14.31%]** | Wrong exact matches of total exact matches returned |
| **Exact Match Precision** | **23 / 23** | **100.00%** | **[85.69%, 100.00%]** | Precision over returned exact matches |
| **Coverage** | **23 / 24** | **95.83%** | **[79.76%, 99.26%]** | Valid exact matches found / generic-expected items |
| **Abstentions** | **0 / 30** | **0.00%** | **[0.00%, 11.35%]** | Precision-first abstentions (below threshold or unstated release) |
| **Negative Control False Matches** | **0 / 20** | **0.00%** | **[0.00%, 16.11%]** | Must be 0% (Rule 1 & Scope v1 enforcement) |
| **Median Per-Tablet Saving** | **23 pairs** | **₹6.00** (IQR: ₹9.57) | Q1: ₹1.67, Q3: ₹11.24 | *indicative; brand prices about 2 years old* |
| **1-Char Typo Candidate Retrieval (Top-3)** | **22 / 30** | **73.33%** | **[55.55%, 85.82%]** | *Candidate retrieval for user confirmation (Rule 4)* |
| **Exact Matches on Unconfirmed Typos** | **0 / 30** | **0.00%** | **[0.00%, 11.35%]** | *Direct exact match on typo query (Rule 3 abstention)* |

---

## 2. Common Brands Benchmark Evaluation (n=30)

Breakdown of all 30 common Indian brands evaluated against ground truth PMBJP generics:

| # | Brand Name | Dosage Form | Release | Expected Code | Actual Code | Match Type | Saving / Unit (₹) | Saving % | Result Status |
| :-: | :--- | :---: | :---: | :-: | :-: | :--- | :-: | :-: | :--- |
| 1 | **Augmentin 625 Duo Tablet** | `tablet` | `IR` | `39` | `39` | `match on assumed release; confirm on strip` | ₹13.58 | 60.8% | **CORRECT_EXACT_MATCH** |
| 2 | **Combiflam Tablet** | `tablet` | `IR` | `14` | `14` | `match on assumed release; confirm on strip` | ₹1.55 | 67.4% | **CORRECT_EXACT_MATCH** |
| 3 | **Montek-LC Tablet** | `tablet` | `IR` | `252` | `252` | `match on assumed release; confirm on strip` | ₹19.02 | 91.0% | **CORRECT_EXACT_MATCH** |
| 4 | **Telma H Tablet** | `tablet` | `IR` | `298` | `298` | `match on assumed release; confirm on strip` | ₹16.07 | 91.0% | **CORRECT_EXACT_MATCH** |
| 5 | **Cifran CT Tablet** | `tablet` | `IR` | `84` | `84` | `match on assumed release; confirm on strip` | ₹10.84 | 74.8% | **CORRECT_EXACT_MATCH** |
| 6 | **Zerodol-P Tablet** | `tablet` | `IR` | `1` | `1` | `match on assumed release; confirm on strip` | ₹5.10 | 84.5% | **CORRECT_EXACT_MATCH** |
| 7 | **Amlong-A Tablet** | `tablet` | `IR` | `263` | `263` | `match on assumed release; confirm on strip` | ₹9.01 | 93.2% | **CORRECT_EXACT_MATCH** |
| 8 | **Glycomet-GP 1 Tablet PR** | `tablet` | `ER` | `904` | `904` | `exact` | ₹6.12 | 78.8% | **CORRECT_EXACT_MATCH** |
| 9 | **EC Pan DSR Capsule** | `capsule` | `ER+DR` | `465` | `465` | `exact` | ₹11.64 | 84.9% | **CORRECT_EXACT_MATCH** |
| 10 | **Cal O Tablet** | `tablet` | `IR` | `220` | `220` | `match on assumed release; confirm on strip` | ₹1.78 | 71.1% | **CORRECT_EXACT_MATCH** |
| 11 | **EC Pan Tablet** | `tablet` | `DR` | `212` | `212` | `exact` | ₹6.07 | 84.2% | **CORRECT_EXACT_MATCH** |
| 12 | **Glycomet 500 SR Tablet** | `tablet` | `ER` | `372` | `372` | `exact` | ₹1.35 | 56.7% | **CORRECT_EXACT_MATCH** |
| 13 | **Mazetol 200 Tablet SR** | `tablet` | `ER` | `1152` | `1152` | `exact` | ₹1.49 | 51.5% | **CORRECT_EXACT_MATCH** |
| 14 | **Lamitor DT 100 Tablet** | `tablet_dispersible` | `IR` | `1448` | `1448` | `match on assumed release; confirm on strip` | ₹28.32 | 88.3% | **CORRECT_EXACT_MATCH** |
| 15 | **Acivir 200 DT Tablet** | `tablet_dispersible` | `IR` | `2657` | `2657` | `match on assumed release; confirm on strip` | ₹5.61 | 66.6% | **CORRECT_EXACT_MATCH** |
| 16 | **Dolo 650 Tablet** | `tablet` | `IR` | `511` | `511` | `match on assumed release; confirm on strip` | ₹1.35 | 58.9% | **CORRECT_EXACT_MATCH** |
| 17 | **Telma 40 Tablet** | `tablet` | `IR` | `300` | `300` | `match on assumed release; confirm on strip` | ₹7.07 | 86.3% | **CORRECT_EXACT_MATCH** |
| 18 | **Azithral 500 Tablet** | `tablet` | `IR` | `72` | `72` | `match on assumed release; confirm on strip` | ₹13.35 | 50.4% | **CORRECT_EXACT_MATCH** |
| 19 | **Ciplox 500 Tablet** | `tablet` | `IR` | `86` | `86` | `match on assumed release; confirm on strip` | ₹2.66 | 58.7% | **CORRECT_EXACT_MATCH** |
| 20 | **Amlong Tablet** | `tablet` | `IR` | `264` | `264` | `match on assumed release; confirm on strip` | ₹2.72 | 84.1% | **CORRECT_EXACT_MATCH** |
| 21 | **Atorva Tablet** | `tablet` | `IR` | `266` | `266` | `match on assumed release; confirm on strip` | ₹6.00 | 87.9% | **CORRECT_EXACT_MATCH** |
| 22 | **Lanoxin Tablet** | `tablet` | `IR` | `428` | `428` | `match on assumed release; confirm on strip` | ₹0.63 | 42.9% | **CORRECT_EXACT_MATCH** |
| 23 | **Brufen 400 Tablet** | `tablet` | `IR` | `16` | `16` | `match on assumed release; confirm on strip` | ₹0.74 | 57.3% | **CORRECT_EXACT_MATCH** |
| 24 | **Thyronorm 100mcg Tablet** | `tablet` | `IR` | `332` | `None` | `none` | - | - | **MISSED_GENERIC_MATCH** |
| 25 | **Rybelsus 3mg Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |
| 26 | **Olumiant 4mg Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |
| 27 | **Anafortan 25 mg/300 mg Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |
| 28 | **Amixide-H Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |
| 29 | **Ajaduo 25mg/5mg Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |
| 30 | **Akurit 4 Tablet** | `tablet` | `IR` | `None` | `None` | `none` | - | - | **CORRECT_NO_MATCH** |

---

## 3. Detailed Analysis of Wrong, Missed, or Abstained Matches

### Total Missed Matches on Generic-Expected Items: 1
#### Brand: `Thyronorm 100mcg Tablet`
- **Expected PMBJP Generic:** Code `332` (`Thyroxine Sodium Tablets IP 100 mcg`)
- **Actual Engine Output:** Match Type: `none`
- **Engine Decision Rationale:** No exact match found: salt differs (unknown or non-whitelisted salt form, or salt not in Jan Aushadhi catalog).
  - *Root Cause Analysis:* Brand packaging raw composition was cataloged as plain `Thyroxine (100mcg)` without the sodium suffix, whereas PMBJP item 332 is `Thyroxine Sodium`. Under Rule 1 whitelist rules, un-whitelisted salt differences prevent exact match ('salt differs').

---

## 4. Negative Controls Benchmark (n=20)

Every negative control represents an intentional failure mode (strength mismatch, salt distinction, release type difference, standard vs dispersible, unsupported formulation). All 20 items must be rejected:

| ID | Query Text | Category | Rule Enforced | Match Type | Status | Intended Rejection Reason |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| 1 | `Dolo 750mg Tablet` | Wrong strength | Rule 1: Strength mismatch never exact matches | `uncertain` | **PASSED_REJECTED** | Wrong strength: Paracetamol 750mg does not exist in PMBJP catalog |
| 2 | `Augmentin 1000mg Tablet` | Negative Control | Rule 3: Abstention on unregistered brand | `uncertain` | **PASSED_REJECTED** | PMBJP has 875mg+125mg; it was rejected because the brand name is not real |
| 3 | `Metoprolol Tartrate 50mg Tablet` | Different salt | Rule 1: Salt form distinction | `uncertain` | **PASSED_REJECTED** | Different salt: Metoprolol Tartrate vs Metoprolol Succinate |
| 4 | `Divalproex Sodium 500mg Tablet` | Different salt | Rule 1: Salt form distinction | `uncertain` | **PASSED_REJECTED** | Different salt: Divalproex Sodium vs Sodium Valproate |
| 5 | `Diclofenac Potassium 50mg Tablet` | Different salt | Rule 1: Salt form distinction | `uncertain` | **PASSED_REJECTED** | Different salt: Diclofenac Potassium vs Diclofenac Sodium |
| 6 | `Hydroxyzine Pamoate 25mg Tablet` | Different salt | Rule 1: Salt form distinction | `uncertain` | **PASSED_REJECTED** | Different salt: Hydroxyzine Pamoate vs Hydroxyzine Hydrochloride |
| 7 | `Ferrous Fumarate 300mg Capsule` | Different salt | Rule 1: Salt form distinction | `uncertain` | **PASSED_REJECTED** | Different salt: Ferrous Fumarate vs Ferrous Sulphate |
| 8 | `Pantoprazole 40mg Plain Immediate Release Tablet` | Release mismatch | Rule 1: Release type mismatch never matches | `uncertain` | **PASSED_REJECTED** | Release mismatch: IR vs Gastro-Resistant DR |
| 9 | `Metformin 500mg Plain Immediate Release Tablet` | Release mismatch | Rule 1: Release type mismatch never matches | `uncertain` | **PASSED_REJECTED** | Release mismatch: IR vs Prolonged Release ER |
| 10 | `Lamotrigine 100mg Standard Non-Dispersible Tablet` | Form mismatch | Rule 1: Form mismatch never matches | `uncertain` | **PASSED_REJECTED** | Form mismatch: Standard tablet vs Dispersible tablet DT |
| 11 | `Aciclovir 400mg Standard Non-Dispersible Tablet` | Form mismatch | Rule 1: Form mismatch never matches | `uncertain` | **PASSED_REJECTED** | Form mismatch: Standard tablet vs Dispersible tablet DT |
| 12 | `Acetylcysteine 600mg Standard Tablet` | Form mismatch | Rule 1: Form mismatch never matches | `uncertain` | **PASSED_REJECTED** | Form mismatch: Standard tablet vs Effervescent tablet |
| 13 | `Dolo-Cold Tablet` | Extra salts | Rule 1: Multi-component composition mismatch | `uncertain` | **PASSED_REJECTED** | Extra salts: Cold combo vs pure Paracetamol 650 |
| 14 | `Combiflam Plus Tablet` | Missing/Extra salt | Rule 1: Salt composition mismatch | `uncertain` | **PASSED_REJECTED** | Missing/Extra salt: Paracetamol+Caffeine vs Paracetamol+Ibuprofen |
| 15 | `Augmentin Duo Oral Suspension` | Unsupported form | Rule 1: Non-solid oral form rejected | `unsupported` | **PASSED_REJECTED** | Unsupported form: Liquid oral suspension |
| 16 | `Ascoril-D Cough Syrup` | Unsupported form | Rule 1: Non-solid oral form rejected | `unsupported` | **PASSED_REJECTED** | Unsupported form: Liquid syrup |
| 17 | `Betnovate-N Cream` | Unsupported form | Rule 1: Non-solid oral form rejected | `unsupported` | **PASSED_REJECTED** | Unsupported form: Topical cream/ointment |
| 18 | `Monocef 1g Injection` | Unsupported form | Rule 1: Non-solid oral form rejected | `unsupported` | **PASSED_REJECTED** | Unsupported form: Intravenous/Intramuscular injection vial |
| 19 | `Ciplox Eye Drops` | Unsupported form | Rule 1: Non-solid oral form rejected | `unsupported` | **PASSED_REJECTED** | Unsupported form: Ophthalmic solution |
| 20 | `Proxyvon Plus Capsule` | Missing component | Rule 1: Safety & component integrity | `uncertain` | **PASSED_REJECTED** | Missing component: Historical banned dextropropoxyphene proxyvon |

---

## 5. Matcher 1-Character Typo Robustness Test (n=30)

*Label: matcher typo robustness, NOT an OCR accuracy test*  
Evaluated by injecting synthetic 1-character perturbations (deletions, substitutions, insertions) into the commercial brand names:

| Original Brand Name | Synthetic Typo Query | Top Retrieved Brand | Confidence | Retrieved in Top-3 |
| :--- | :--- | :--- | :---: | :---: |
| `Augmentin 625 Duo Tablet` | `Aaugmentin 625 Duo Tablet` | `Augmentin 625 Duo Tablet` | **74.8%** | PASSED |
| `Combiflam Tablet` | `Comwiflam Tablet` | `Combiflam Tablet` | **7.1%** | PASSED |
| `Montek-LC Tablet` | `Monte-LC Tablet` | `Monte 10mg Tablet` | **83.4%** | MISSED |
| `Telma H Tablet` | `Tema H Tablet` | `Temax H 40mg Tablet` | **29.9%** | MISSED |
| `Cifran CT Tablet` | `Cifrbn CT Tablet` | `Cifran CT Tablet` | **26.2%** | PASSED |
| `Zerodol-P Tablet` | `Zrodol-P Tablet` | `Prodol 500mg Tablet` | **4.4%** | PASSED |
| `Amlong-A Tablet` | `Amleong-A Tablet` | `Amleod 5mg Tablet` | **31.7%** | MISSED |
| `Glycomet-GP 1 Tablet PR` | `Glycomnt-GP 1 Tablet PR` | `Glycomet-GP 1 Tablet PR` | **82.9%** | PASSED |
| `EC Pan DSR Capsule` | `EC Pan DSR Capule` | `EC Pan DSR Capsule` | **67.7%** | PASSED |
| `Cal O Tablet` | `Cal O Tahlet` | `Cal O Tablet` | **60.3%** | PASSED |
| `EC Pan Tablet` | `EC Pan Tblet` | `EC Pan Tablet` | **77.3%** | PASSED |
| `Glycomet 500 SR Tablet` | `Gloycomet 500 SR Tablet` | `Glycomet 500 SR Tablet` | **9.3%** | PASSED |
| `Mazetol 200 Tablet SR` | `Mazerol 200 Tablet SR` | `Mazetol SR 200 Tablet` | **23.7%** | MISSED |
| `Lamitor DT 100 Tablet` | `Laeitor DT 100 Tablet` | `Lamitor DT 100 Tablet` | **8.2%** | PASSED |
| `Acivir 200 DT Tablet` | `Apcivir 200 DT Tablet` | `Acivir 200 DT Tablet` | **16.2%** | PASSED |
| `Dolo 650 Tablet` | `Doso 650 Tablet` | `P 650 Tablet` | **4.1%** | PASSED |
| `Telma 40 Tablet` | `Tgelma 40 Tablet` | `Telma 40 Tablet` | **14.8%** | PASSED |
| `Azithral 500 Tablet` | `Auithral 500 Tablet` | `Azithral 500 Tablet` | **28.0%** | PASSED |
| `Ciplox 500 Tablet` | `Cipox 500 Tablet` | `Cipoxa 500mg Tablet` | **56.6%** | MISSED |
| `Amlong Tablet` | `Among Tablet` | `Among 6 Tablet` | **94.7%** | MISSED |
| `Atorva Tablet` | `Atcorva Tablet` | `Atcor 20mg Tablet` | **42.5%** | MISSED |
| `Lanoxin Tablet` | `Lanoin Tablet` | `Lano 5mg Tablet` | **10.1%** | MISSED |
| `Brufen 400 Tablet` | `Bufen 400 Tablet` | `Bufex Plus 400 mg/500 mg Tablet` | **6.8%** | PASSED |
| `Thyronorm 100mcg Tablet` | `Thyonorm 100mcg Tablet` | `Thyone 100mcg Tablet` | **74.2%** | PASSED |
| `Rybelsus 3mg Tablet` | `Rybnlsus 3mg Tablet` | `Rybelsus 3mg Tablet` | **62.4%** | PASSED |
| `Olumiant 4mg Tablet` | `Oyumiant 4mg Tablet` | `Olumiant 4mg Tablet` | **14.3%** | PASSED |
| `Anafortan 25 mg/300 mg Tablet` | `Anafwortan 25 mg/300 mg Tablet` | `Anafortan 25 mg/300 mg Tablet` | **72.3%** | PASSED |
| `Amixide-H Tablet` | `Admixide-H Tablet` | `Admine 400 Tablet` | **8.6%** | PASSED |
| `Ajaduo 25mg/5mg Tablet` | `Ajawuo 25mg/5mg Tablet` | `Ajaduo 25mg/5mg Tablet` | **65.8%** | PASSED |
| `Akurit 4 Tablet` | `Aurit 4 Tablet` | `Akurit 4 Tablet` | **1.3%** | PASSED |

- **Candidate Retrieval for User Confirmation (Rule 4):** **22 / 30 (73.33%)** [Wilson 95% CI: 55.55% - 85.82%]
- **Exact Matches Returned on Unconfirmed Typos (Rule 3):** **0 / 30 (0.00%)** [Wilson 95% CI: 0.00% - 11.35%]

---
