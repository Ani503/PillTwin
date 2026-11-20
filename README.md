# PillTwin

PillTwin finds the Jan Aushadhi (PMBJP) generic equivalent for Indian commercial brand medicines.
Users search by typing a medicine brand name or scanning a medicine blister strip photo.
The app displays side-by-side active salt compositions and indicative per-tablet price savings.

Not medical advice. Prototype.

Live app: (add after deploy)

Contains a processed copy of third-party data; see THIRD_PARTY_LICENSES.md.

---

## Architecture

`data -> canonical key -> matcher -> OCR -> confirm -> result`

1. **data**: Clean PMBJP Jan Aushadhi generic catalog and Indian medicine commercial brand catalog.
2. **canonical key**: Deterministic representation normalizing active salt names, strengths, solid dosage forms, and release mechanisms (`salt:strength|form|release`).
3. **matcher**: Substring and n-gram similarity engine with Platt-calibrated confidence scores and precision-first abstention.
4. **OCR**: In-memory text extraction using Tesseract OCR, image deskewing, contrast enhancement, and packaging noise filtering.
5. **confirm**: User confirmation step where detected candidate names are displayed for review; OCR output never auto-submits.
6. **result**: Side-by-side card showing commercial brand, Jan Aushadhi generic equivalent, price list date, caution notices, and calculated savings.

---

## Safety Rules

1. **Strict Exact Match**: Generic equivalents require identical active pharmaceutical ingredients, identical unit strengths, identical dosage forms (tablet vs capsule), and matching release profiles (IR vs ER/DR).
2. **Transparent Price Context**: Generic prices display `price_list_date: 2026-11-07`. Commercial brand prices are marked as a historical snapshot (~2 years old) with indicative savings.
3. **Safety Abstention**: The engine abstains whenever confidence is below threshold, formulation details differ, or release kinetics are unstated on modified-release drugs.
4. **User Confirmation Required**: Camera and OCR inputs never show prices directly; users must select and confirm the medicine name first.
5. **Doctor Supervision on Caution Drugs**: Narrow therapeutic index drugs (e.g., warfarin, levothyroxine, antiepileptics) display mandatory clinical review warnings.
6. **Zero Image Storage**: Blister strip images are processed purely in memory to read text; photos are never written to disk or stored.

---

## Evaluation and Limits

- **Benchmark Size**: n=30 brands, key drafted by the agent and not human-verified; OCR on 10 real photos plus synthetic images; accuracy not established.
- **Common Brands Test**: 23 of 30 items produced exact matches to Jan Aushadhi entries; 1 missed due to salt naming differences; 6 items had no generic equivalent in the PMBJP catalog.
- **Negative Controls Test**: 0 of 20 intentional mismatch controls (wrong strengths, distinct salts, unsupported liquid forms) produced false matches (20 of 20 rejected).
- **OCR Limitations**: Real-world strip photos suffer from metallic foil glare, curvature, motion blur, and low lighting; automated character extraction is noisy, which is why explicit user confirmation is mandatory.

---

## Data Sources, Dates, and Licences

- **PMBJP Price List**: Pharmaceuticals & Medical Devices Bureau of India (PMBI).
  - Price list date: 2026-11-07 (PDF metadata date; official effective date not stated)
- **Indian Medicine Dataset**: `junioralive/Indian-Medicine-Dataset` (MIT, Copyright (c) 2024 JuniorAlive, commit d584adf).
  - Data download date: 2026-11-19
  - Notice: origin of listings not stated; may contain errors.

---

## How to Run and Test

Run test suite:
```bash
make test
```

Run application locally:
```bash
make app
```
