import os
import io
import random
import glob
from typing import List, Dict, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from src.ocr.engine import PillTwinOCR

def generate_synthetic_strip(
    brand_name: str,
    composition_line: str,
    batch_no: str = "B.No. X8921",
    mfg_exp: str = "MFG: 03/2026  EXP: 02/2028",
    mrp: str = "M.R.P. Rs. 145.50 Incl. of all taxes",
    mfg_by: str = "Manufactured by: Torrent Pharmaceuticals Ltd., Baddi",
    rotation_deg: float = 0.0,
    blur: bool = False,
    contrast_factor: float = 1.0
) -> bytes:
    """Generates an in-memory synthetic medicine packaging strip image with realistic noise and variations."""
    width, height = 800, 320
    img = Image.new('RGB', (width, height), color=(250, 250, 248))
    draw = ImageDraw.Draw(img)

    # Brand Header with adequate margin
    draw.text((45, 40), brand_name.upper(), fill=(15, 23, 42))
    # Composition / Generic line
    draw.text((45, 95), composition_line, fill=(51, 65, 85))
    # Regulatory & Batch noise lines
    draw.text((45, 145), f"{batch_no}   {mfg_exp}", fill=(100, 116, 139))
    draw.text((45, 185), mrp, fill=(100, 116, 139))
    draw.text((45, 225), mfg_by, fill=(148, 163, 184))

    # Apply contrast alteration
    if contrast_factor != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)

    # Apply blur
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.7))

    # Apply rotation with expand=True so text is never clipped
    if abs(rotation_deg) > 0.1:
        img = img.rotate(rotation_deg, resample=Image.BICUBIC, fillcolor=(250, 250, 248), expand=True)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

SYNTHETIC_STRIP_SPECS = [
    {
        "true_brand": "Dolo 650 Tablet",
        "brand_text": "DOLO 650 Tablets",
        "comp_text": "Paracetamol Tablets IP 650 mg",
        "rotation": 3.5,
        "contrast": 1.1,
        "blur": False
    },
    {
        "true_brand": "Augmentin 625 Duo Tablet",
        "brand_text": "AUGMENTIN 625 DUO",
        "comp_text": "Amoxycillin and Potassium Clavulanate Tablets IP (500mg + 125mg)",
        "rotation": -4.0,
        "contrast": 0.95,
        "blur": False
    },
    {
        "true_brand": "Pan 40 Tablet",
        "brand_text": "PAN 40 Tablets",
        "comp_text": "Pantoprazole Gastro-Resistant Tablets IP 40 mg",
        "rotation": 2.0,
        "contrast": 1.0,
        "blur": True
    },
    {
        "true_brand": "Combiflam Tablet",
        "brand_text": "COMBIFLAM Tablets",
        "comp_text": "Ibuprofen and Paracetamol Tablets (400mg + 325mg)",
        "rotation": -2.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Telma 40 Tablet",
        "brand_text": "TELMA 40",
        "comp_text": "Telmisartan Tablets IP 40 mg",
        "rotation": 5.0,
        "contrast": 0.9,
        "blur": False
    },
    {
        "true_brand": "Azithral 500 Tablet",
        "brand_text": "AZITHRAL 500",
        "comp_text": "Azithromycin Tablets IP 500 mg",
        "rotation": -3.0,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Montek-LC Tablet",
        "brand_text": "MONTEK-LC Tablets",
        "comp_text": "Montelukast Sodium 10mg & Levocetirizine 5mg Tablets",
        "rotation": 1.5,
        "contrast": 1.1,
        "blur": False
    },
    {
        "true_brand": "Glycomet 500 SR Tablet",
        "brand_text": "GLYCOMET 500 SR",
        "comp_text": "Metformin Hydrochloride Sustained-Release Tablets IP 500 mg",
        "rotation": -5.0,
        "contrast": 0.9,
        "blur": False
    },
    {
        "true_brand": "Lamitor DT 100 Tablet",
        "brand_text": "LAMITOR DT 100",
        "comp_text": "Lamotrigine Dispersible Tablets 100 mg",
        "rotation": 2.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Cifran CT Tablet",
        "brand_text": "CIFRAN CT Tablets",
        "comp_text": "Ciprofloxacin 500mg and Tinidazole 600mg Tablets",
        "rotation": -2.0,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Brufen 400 Tablet",
        "brand_text": "BRUFEN 400",
        "comp_text": "Ibuprofen Tablets IP 400 mg",
        "rotation": 4.0,
        "contrast": 0.95,
        "blur": False
    },
    {
        "true_brand": "Zerodol-P Tablet",
        "brand_text": "ZERODOL-P",
        "comp_text": "Aceclofenac 100mg and Paracetamol 325mg Tablets",
        "rotation": -3.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Mazetol 200 Tablet SR",
        "brand_text": "MAZETOL SR 200",
        "comp_text": "Carbamazepine Prolonged-Release Tablets IP 200 mg",
        "rotation": 1.0,
        "contrast": 1.0,
        "blur": True
    },
    {
        "true_brand": "Acivir 200 DT Tablet",
        "brand_text": "ACIVIR 200 DT",
        "comp_text": "Aciclovir Dispersible Tablets IP 200 mg",
        "rotation": -4.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Rybelsus 3mg Tablet",
        "brand_text": "RYBELSUS 3 mg",
        "comp_text": "Semaglutide Tablets 3 mg",
        "rotation": 2.0,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Cal O Tablet",
        "brand_text": "CAL O Tablets",
        "comp_text": "Calcium Carbonate 1250mg & Vitamin D3 250 IU Tablets",
        "rotation": -2.0,
        "contrast": 1.1,
        "blur": False
    },
    {
        "true_brand": "EC Pan Tablet",
        "brand_text": "EC PAN 40",
        "comp_text": "Pantoprazole Enteric Coated Tablets IP 40 mg",
        "rotation": 3.0,
        "contrast": 0.9,
        "blur": False
    },
    {
        "true_brand": "Amixide-H Tablet",
        "brand_text": "AMIXIDE-H Tablets",
        "comp_text": "Amitriptyline 12.5mg and Chlordiazepoxide 5mg Tablets",
        "rotation": -1.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Atorva Tablet",
        "brand_text": "ATORVA 20",
        "comp_text": "Atorvastatin Calcium Tablets IP 20 mg",
        "rotation": 4.5,
        "contrast": 1.0,
        "blur": False
    },
    {
        "true_brand": "Lanoxin Tablet",
        "brand_text": "LANOXIN Tablets",
        "comp_text": "Digoxin Tablets IP 0.25 mg",
        "rotation": -2.0,
        "contrast": 1.0,
        "blur": False
    }
]

def run_synthetic_test():
    print("=== PILLTWIN PHASE 3: SYNTHETIC OCR BENCHMARK ===")
    print("Label: synthetic test; real strip accuracy not measured\n")

    ocr_system = PillTwinOCR()
    engine_name = ocr_system.engine_name
    print(f"[*] OCR Engine in use: {engine_name}")

    results = []
    exact_matches_without_confirmation = 0
    top_5_hits = 0

    print("\n--- Running 20 Synthetic Medicine Strip Packaging Tests ---\n")

    for i, spec in enumerate(SYNTHETIC_STRIP_SPECS, 1):
        img_bytes = generate_synthetic_strip(
            brand_name=spec["brand_text"],
            composition_line=spec["comp_text"],
            rotation_deg=spec["rotation"],
            blur=spec["blur"],
            contrast_factor=spec["contrast"]
        )

        # Run OCR
        scan_res = ocr_system.scan_strip_photo(img_bytes)

        # Check safety: must NEVER produce exact match
        if scan_res.exact_match_produced:
            exact_matches_without_confirmation += 1

        # Check if true brand is in top 5 suggested candidates
        top_5_names = [b['brand_name'].lower() for b in scan_res.suggested_brands]
        target_name = spec["true_brand"].lower()
        
        # Check matching with alphanumeric normalization
        import re
        def _clean(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', str(s).lower())

        c_target = _clean(spec["true_brand"])
        hit = any(
            c_target in _clean(name) or _clean(name) in c_target or
            _clean(spec["true_brand"].split()[0]) in _clean(name)
            for name in top_5_names
        )
        if hit:
            top_5_hits += 1

        top_cand_str = scan_res.suggested_brands[0]['brand_name'] if scan_res.suggested_brands else "None"
        top_conf_str = f"{scan_res.suggested_brands[0]['calibrated_confidence']*100:.1f}%" if scan_res.suggested_brands else "0%"

        results.append({
            "idx": i,
            "true_brand": spec["true_brand"],
            "raw_ocr_text": " | ".join(scan_res.raw_lines),
            "top_candidate": top_cand_str,
            "confidence": top_conf_str,
            "in_top_5": hit,
            "exact_produced": scan_res.exact_match_produced
        })

        print(f"[{i:02d}/20] True: {spec['true_brand']}")
        print(f"     OCR Text: {' | '.join(scan_res.raw_lines)}")
        print(f"     Top Candidate: {top_cand_str} ({top_conf_str}) | In Top 5: {'YES' if hit else 'NO'} | Exact Match Produced: {scan_res.exact_match_produced}")
        print()

    # Check for any real photos in data/photos/
    real_photo_files = glob.glob("data/photos/*.*")
    if real_photo_files:
        print(f"\n--- Running Real Photos in data/photos/ (n={len(real_photo_files)}) ---")
        for pfile in real_photo_files:
            try:
                with open(pfile, "rb") as f:
                    pbytes = f.read()
                pres = ocr_system.scan_strip_photo(pbytes)
                if pres.exact_match_produced:
                    exact_matches_without_confirmation += 1
                print(f"[Real Photo] {pfile} -> OCR Text: {' | '.join(pres.raw_lines[:3])} | Exact Produced: {pres.exact_match_produced}")
            except Exception as e:
                print(f"[Real Photo] {pfile} -> Error: {e}")
    else:
        print("\n[*] data/photos/ contains 0 real photo files. (Synthetic test completed).")

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Engine in use: {engine_name}")
    print(f"Total synthetic images evaluated: {len(SYNTHETIC_STRIP_SPECS)}")
    print(f"True brand retrieved in Top 5: {top_5_hits} / {len(SYNTHETIC_STRIP_SPECS)} ({top_5_hits/len(SYNTHETIC_STRIP_SPECS)*100:.1f}%)")
    print(f"Exact matches produced without user confirmation: {exact_matches_without_confirmation} (MUST BE 0)")
    print("Label: synthetic test; real strip accuracy not measured")

if __name__ == "__main__":
    run_synthetic_test()
