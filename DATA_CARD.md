# Data Card: PillTwin

## 1. PMBJP Official Formulary and Price List
- Source: Pharmaceuticals & Medical Devices Bureau of India (PMBI), Pradhan Mantri Bhartiya Janaushadhi Pariyojana.
- Price List Date: 2026-11-07 (PDF metadata date; official effective date not stated)
- Data Download Date: 2026-11-19
- Scope: Oral solid tablets and capsules only. Non-solid oral dosage forms and surgical items are excluded.
- Processed Generic Items: 1,156 entries mapping to 1,150 unique canonical keys.

## 2. Indian Medicine Dataset
- Source: junioralive/Indian-Medicine-Dataset (MIT, Copyright (c) 2024 JuniorAlive, commit d584adf)
- Price List Date: 2026-11-07
- Data Download Date: 2026-11-19
- Notice: origin of listings not stated; may contain errors
- Price Note: Commercial brand prices reflect a historical catalog snapshot (~2 years old) and savings are indicative only.

## 3. Processed Datasets (data/processed/)
- `pmbjp_clean.parquet` / `pmbjp_clean.csv`: Clean PMBJP solid-oral items.
- `formulary_index.json`: Canonical key lookup index for Jan Aushadhi generic twins.
- `brand_clean.parquet`: Clean brand catalog filtered and optimized for 512 MB memory footprint (20,579 rows, 691 KB).
- `matcher_calibration.json`: Platt scaling calibration parameters for brand matching confidence.
