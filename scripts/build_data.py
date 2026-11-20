import os
import sys
import re
import json
import yaml
import pypdf
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parsers.canonical import (
    parse_composition,
    parse_pack_size,
    check_caution_drug
)

def build_pmbjp(pdf_path, caution_config):
    print(f"[Phase 1] Building PMBJP catalog from {pdf_path}...")
    reader = pypdf.PdfReader(pdf_path)

    skip_keywords = [
        'PMBI -', 'Page ', 'GOVERNMENT OF INDIA', 'Pradhan Mantri', 'Pharmaceuticals &',
        'Total Products', 'Therapeutic Groups', 'Quality Standard', 'Official Portal',
        'SURGICAL &', 'CARDIOVASCULAR', 'CENTRAL NERVOUS', 'ANTIBIOTICS', 'ANTI-DIABETIC',
        'GASTROINTESTINAL', 'Tested', 'SortingView',
        'Consumer Information', 'from WHO-GMP', 'Maximum Retail', 'SR. DRUG CODE'
    ]

    all_lines = []
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        for line in text.splitlines():
            line = line.strip()
            if not line or any(h in line for h in skip_keywords):
                continue
            all_lines.append((page_idx + 1, line))

    rows = []
    current_row = None

    for page_num, line in all_lines:
        m_start = re.match(r'^(\d+)\s+(\d+)(?:\s+(.*))?$', line)
        is_true_start = False
        if m_start:
            sr_val = int(m_start.group(1))
            if current_row is None and sr_val == 1:
                is_true_start = True
            elif current_row is not None and sr_val == current_row['sr'] + 1:
                is_true_start = True
            elif current_row is not None and sr_val > current_row['sr'] and sr_val <= current_row['sr'] + 2:
                is_true_start = True

        if is_true_start:
            if current_row:
                rows.append(current_row)
            rest = m_start.group(3) or ''
            current_row = {
                'sr': int(m_start.group(1)),
                'drug_code': m_start.group(2),
                'text': rest,
                'page': page_num
            }
        else:
            if current_row:
                if current_row['text']:
                    current_row['text'] += ' ' + line
                else:
                    current_row['text'] = line

    if current_row:
        rows.append(current_row)

    print(f"  Total raw lines assembled into PMBJP items: {len(rows)}")

    clean_records = []
    excluded_counts = {
        'zero_mrp': 0,
        'non_solid_oral': 0,
        'surgical': 0,
        'parse_error': 0
    }

    for r in rows:
        m_p = re.search(r'₹\s*([\d\.,]+)\s*(.*)$', r['text'])
        if not m_p:
            excluded_counts['parse_error'] += 1
            continue
        mrp = float(m_p.group(1).replace(',', ''))
        group = m_p.group(2).strip()
        raw_desc = r['text'][:m_p.start()].strip()

        # Check surgicals
        is_surg = bool(re.search(r'surgical|device|consumable', group, re.I) or
                       re.search(r'bandage|cannula|gloves|syringe|needle|catheter|cotton|tube|tape|swab|mask|dressing|kit|gauze|blade|suture', raw_desc, re.I))
        if is_surg:
            excluded_counts['surgical'] += 1
            continue

        # Check zero mrp
        if mrp <= 0.0:
            excluded_counts['zero_mrp'] += 1
            continue

        # Extract unit size
        m_unit = re.search(r'\s+((?:\d+[\'’]s|\d+\s*ml|\d+\s*g(?:m)?|\d+\s*strips?|\d+\s*tablets?|\d+\s*capsules?|vial.*?|bottle.*?|one in.*?|each|strip of \d+.*?|box.*?|pack.*?|\d+\s*sachets?|tube.*?|piece.*?|pair.*?|\d+[\'’]S))$', raw_desc, re.I)
        if m_unit:
            unit_size = m_unit.group(1).strip()
            generic_name = raw_desc[:m_unit.start()].strip()
        else:
            parts = raw_desc.rsplit(' ', 1)
            if len(parts) == 2 and ("'s" in parts[1].lower() or parts[1].isdigit()):
                generic_name, unit_size = parts[0], parts[1]
            else:
                generic_name, unit_size = raw_desc, "10's"

        pack_units, _ = parse_pack_size(unit_size)
        if not pack_units or pack_units <= 0:
            pack_units, _ = parse_pack_size(raw_desc)
        if not pack_units or pack_units <= 0:
            pack_units = 10 # standard default pack for solid oral tablets if not parseable

        # Parse canonical key
        parsed = parse_composition(generic_name, form_hint=raw_desc, name_hint=raw_desc)
        if not parsed.is_solid_oral or not parsed.canonical_key:
            excluded_counts['non_solid_oral'] += 1
            continue

        # Caution check
        caution_flags = check_caution_drug(parsed.salts, caution_config)

        price_per_unit = round(mrp / pack_units, 4)

        clean_records.append({
            'sr_no': r['sr'],
            'drug_code': r['drug_code'],
            'generic_name': generic_name,
            'raw_desc': raw_desc,
            'unit_size': unit_size,
            'pack_units': pack_units,
            'mrp': mrp,
            'price_per_unit': price_per_unit,
            'therapeutic_group': group,
            'dosage_form': parsed.dosage_form,
            'release_type': parsed.release_type,
            'release_type_source': parsed.release_type_source,
            'release_type_note': parsed.release_type_note,
            'canonical_key': parsed.canonical_key,
            'has_caution': len(caution_flags) > 0,
            'caution_json': json.dumps(caution_flags),
            'price_list_export_date': "2026-11-07",
            'data_download_date': "2026-11-19",
            'price_list_date': "2026-11-07"
        })

    df_pmbjp = pd.DataFrame(clean_records)
    print(f"  PMBJP clean active solid-oral items: {len(df_pmbjp)}")
    print(f"  PMBJP exclusions: {excluded_counts}")
    return df_pmbjp

def build_brand_data(brand_csv_path, updated_csv_path, pmbjp_keys, caution_config):
    print(f"[Phase 1] Building brand dataset from {brand_csv_path}...")
    df_raw = pd.read_csv(brand_csv_path)
    total_raw = len(df_raw)

    # Check updated csv for enriched salt_composition
    salt_comp_map = {}
    if os.path.exists(updated_csv_path):
        print(f"  Enriching with full multi-salt compositions from {updated_csv_path}...")
        df_up = pd.read_csv(updated_csv_path, usecols=['id', 'salt_composition'])
        salt_comp_map = dict(zip(df_up['id'], df_up['salt_composition'].fillna('')))

    # Filter to oral solids (tablets & capsules)
    is_solid = df_raw['pack_size_label'].str.contains(r'tablet|capsule', case=False, na=False)
    df_solid = df_raw[is_solid].copy()
    print(f"  Oral solid rows in brand dataset: {len(df_solid)} / {total_raw} ({len(df_solid)/total_raw:.1%})")

    clean_brands = []
    unparseable_count = 0
    price_zero_count = 0

    for _, r in df_solid.iterrows():
        price = float(r['price(₹)'])
        if price <= 0.0:
            price_zero_count += 1
            continue

        # Get best composition string
        med_id = r['id']
        enriched_comp = salt_comp_map.get(med_id, '')
        if enriched_comp and '+' in enriched_comp:
            comp_str = enriched_comp
        else:
            c1 = str(r['short_composition1']) if pd.notna(r['short_composition1']) else ''
            c2 = str(r['short_composition2']) if pd.notna(r['short_composition2']) else ''
            comp_str = c1 + (" + " + c2 if c2 else "")

        pack_label = str(r['pack_size_label'])
        med_name = str(r['name'])

        # Parse canonical key
        parsed = parse_composition(comp_str, form_hint=pack_label, name_hint=med_name)
        if not parsed.canonical_key or not parsed.is_solid_oral:
            unparseable_count += 1
            continue

        pack_units, _ = parse_pack_size(pack_label)
        if not pack_units or pack_units <= 0:
            pack_units = 10 # default fallback

        price_per_unit = round(price / pack_units, 4)
        has_exact = parsed.canonical_key in pmbjp_keys

        # Caution check
        caution_flags = check_caution_drug(parsed.salts, caution_config)

        clean_brands.append({
            'brand_id': int(med_id),
            'brand_name': med_name,
            'manufacturer': str(r['manufacturer_name']),
            'pack_size_label': pack_label,
            'pack_units': pack_units,
            'price': price,
            'price_per_unit': price_per_unit,
            'is_discontinued': bool(r['Is_discontinued']),
            'raw_composition': comp_str,
            'dosage_form': parsed.dosage_form,
            'release_type': parsed.release_type,
            'release_type_source': parsed.release_type_source,
            'release_type_note': parsed.release_type_note,
            'canonical_key': parsed.canonical_key,
            'has_exact_generic_match': has_exact,
            'has_caution': len(caution_flags) > 0,
            'caution_json': json.dumps(caution_flags)
        })

    df_clean_brand = pd.DataFrame(clean_brands)
    print(f"  Brand clean active solid-oral rows: {len(df_clean_brand)}")
    print(f"  Rows excluded due to zero price: {price_zero_count}, unparseable: {unparseable_count}")
    matched_share = df_clean_brand['has_exact_generic_match'].mean()
    print(f"  Share of brand products with EXACT PMBJP generic match: {matched_share:.1%}")
    return df_clean_brand

def main():
    os.makedirs('data/processed', exist_ok=True)
    pdf_path = 'data/raw/pmbjp_mrp_list_2026.pdf'
    brand_csv = 'data/raw/indian_medicine_data.csv'
    updated_csv = 'data/raw/updated_indian_medicine_data.csv'
    caution_path = 'config/caution_drugs.yaml'

    with open(caution_path, 'r') as f:
        caution_config = yaml.safe_load(f)

    # 1. Build PMBJP
    df_pmbjp = build_pmbjp(pdf_path, caution_config)

    # Build formulary index (canonical_key -> list of PMBJP products)
    formulary_index = {}
    for _, r in df_pmbjp.iterrows():
        key = r['canonical_key']
        if key not in formulary_index:
            formulary_index[key] = []
        formulary_index[key].append({
            'drug_code': r['drug_code'],
            'generic_name': r['generic_name'],
            'unit_size': r['unit_size'],
            'pack_units': int(r['pack_units']),
            'mrp': float(r['mrp']),
            'price_per_unit': float(r['price_per_unit']),
            'therapeutic_group': r['therapeutic_group'],
            'dosage_form': r['dosage_form'],
            'release_type': r['release_type'],
            'release_type_source': r['release_type_source'],
            'release_type_note': r['release_type_note'],
            'has_caution': bool(r['has_caution']),
            'caution_json': r['caution_json'],
            'price_list_export_date': r['price_list_export_date'],
            'data_download_date': r['data_download_date'],
            'price_list_date': r['price_list_date']
        })

    for k in formulary_index:
        # Sort descending by price_per_unit so highest price per unit is primary (rule: never pick cheaper one)
        formulary_index[k].sort(key=lambda x: (-x['price_per_unit'], int(x['drug_code'])))
        is_ambiguous = len(formulary_index[k]) > 1
        for item in formulary_index[k]:
            item['is_price_ambiguous'] = is_ambiguous
            item['price_status'] = "price ambiguous" if is_ambiguous else "normal"

    pmbjp_keys = set(formulary_index.keys())
    print(f"  Total unique canonical PMBJP keys indexed: {len(pmbjp_keys)}")

    # 2. Build Brand Dataset
    df_brand = build_brand_data(brand_csv, updated_csv, pmbjp_keys, caution_config)

    # 3. Save artifacts
    pmbjp_parquet = 'data/processed/pmbjp_clean.parquet'
    pmbjp_csv = 'data/processed/pmbjp_clean.csv'
    brand_parquet = 'data/processed/brand_clean.parquet'
    formulary_path = 'data/processed/formulary_index.json'
    summary_path = 'data/processed/build_summary.json'

    print(f"  Saving PMBJP clean table to {pmbjp_parquet} and {pmbjp_csv}...")
    df_pmbjp.to_parquet(pmbjp_parquet, index=False)
    df_pmbjp.to_csv(pmbjp_csv, index=False)

    print(f"  Saving Brand clean table to {brand_parquet}...")
    df_brand.to_parquet(brand_parquet, index=False)

    print(f"  Saving Formulary index to {formulary_path}...")
    with open(formulary_path, 'w', encoding='utf-8') as f:
        json.dump(formulary_index, f, indent=2)

    build_summary = {
        'build_timestamp': "2026-11-20T00:30:00",
        'pmbjp_total_raw_rows': 2439,
        'pmbjp_clean_solid_oral_count': len(df_pmbjp),
        'pmbjp_unique_canonical_keys': len(pmbjp_keys),
        'price_list_export_date': "2026-11-07",
        'price_list_date_source': "PDF creation date; official effective date not stated",
        'data_download_date': "2026-11-19",
        'price_list_date': "2026-11-07",
        'data_age_note': "Brand prices are from a historical snapshot (commit d584adf) and may be outdated. Generic prices reflect the PMBJP price list exported on 2026-11-07. All savings are indicative information, not real-time quotes or medical advice.",
        'brand_total_raw_rows': 253973,
        'brand_clean_solid_oral_count': len(df_brand),
        'brand_with_exact_pmbjp_match': int(df_brand['has_exact_generic_match'].sum()),
        'brand_exact_match_share': float(df_brand['has_exact_generic_match'].mean()),
        'brand_caution_drug_count': int(df_brand['has_caution'].sum()),
        'pmbjp_caution_drug_count': int(df_pmbjp['has_caution'].sum())
    }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(build_summary, f, indent=2)

    print("Phase 1 Data Build completed successfully.")
    print(f"Summary: {json.dumps(build_summary, indent=2)}")

if __name__ == '__main__':
    main()
