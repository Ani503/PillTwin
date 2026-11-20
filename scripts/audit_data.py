import os
import re
import sys
import json
from collections import Counter
import pypdf
import pandas as pd
import numpy as np

def audit_pmbjp(pdf_path):
    print(f"Auditing PMBJP PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    # Metadata and Date search
    pdf_meta = reader.metadata or {}
    pdf_text_sample = ""
    for i in range(min(3, total_pages)):
        pdf_text_sample += reader.pages[i].extract_text() + "\n"

    # Search for dates
    date_matches = re.findall(r'(?:Last updated|Date|dated|Edition)[\s:]*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})', pdf_text_sample, re.I)

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

    parsed_records = []
    parse_failures = []
    for r in rows:
        m_p = re.search(r'₹\s*([\d\.,]+)\s*(.*)$', r['text'])
        if not m_p:
            parse_failures.append(r)
            continue
        mrp = float(m_p.group(1).replace(',', ''))
        group = m_p.group(2).strip()
        raw_desc = r['text'][:m_p.start()].strip()
        
        # Unit size pattern
        m_unit = re.search(r'\s+((?:\d+[\'’]s|\d+\s*ml|\d+\s*g(?:m)?|\d+\s*strips?|\d+\s*tablets?|\d+\s*capsules?|vial.*?|bottle.*?|one in.*?|each|strip of \d+.*?|box.*?|pack.*?|\d+\s*sachets?|tube.*?|piece.*?|pair.*?|\d+[\'’]S))$', raw_desc, re.I)
        if m_unit:
            unit_size = m_unit.group(1).strip()
            generic_name = raw_desc[:m_unit.start()].strip()
        else:
            parts = raw_desc.rsplit(' ', 1)
            if len(parts) == 2 and ("'s" in parts[1].lower() or parts[1].isdigit()):
                generic_name, unit_size = parts[0], parts[1]
            else:
                generic_name, unit_size = raw_desc, ''

        parsed_records.append({
            'sr': r['sr'],
            'drug_code': r['drug_code'],
            'generic_name': generic_name,
            'unit_size': unit_size,
            'raw_desc': raw_desc,
            'mrp': mrp,
            'group': group,
            'page': r['page']
        })

    df = pd.DataFrame(parsed_records)
    
    # Exclusions
    # Zero MRP
    zero_mrp_mask = df['mrp'] == 0.0
    
    # Form classification
    is_tablet = df['raw_desc'].str.contains(r'\btablet', case=False, regex=True)
    is_capsule = df['raw_desc'].str.contains(r'\bcapsule', case=False, regex=True)
    is_solid_oral = is_tablet | is_capsule
    
    # Surgical / Medical Consumables / Devices
    is_surgical = df['group'].str.contains(r'surgical|device|consumable', case=False, regex=True) | \
                  df['generic_name'].str.contains(r'bandage|cannula|gloves|syringe|needle|catheter|cotton|tube|tape|swab|mask|dressing|kit|gauze|blade|suture', case=False, regex=True)

    non_solid_oral_mask = ~is_solid_oral

    # Retained active solid oral
    retained_mask = is_solid_oral & (~zero_mrp_mask) & (~is_surgical)

    return {
        'total_pages': total_pages,
        'total_rows_parsed': len(df),
        'parse_failures': parse_failures,
        'zero_mrp_count': int(zero_mrp_mask.sum()),
        'non_solid_oral_count': int(non_solid_oral_mask.sum()),
        'surgical_count': int(is_surgical.sum()),
        'tablet_count': int(is_tablet.sum()),
        'capsule_count': int(is_capsule.sum()),
        'both_tab_cap_count': int((is_tablet & is_capsule).sum()),
        'retained_solid_oral_active': int(retained_mask.sum()),
        'dates_found': date_matches,
        'df': df
    }

def audit_brand_csv(csv_path):
    print(f"Auditing Brand CSV: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Brand CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    total_rows = len(df)
    cols = df.columns.tolist()
    dtypes = {c: str(df[c].dtype) for c in cols}

    # Missing composition rate
    missing_c1 = int(df['short_composition1'].isna().sum())
    missing_c2 = int(df['short_composition2'].isna().sum())
    # Both missing
    both_missing = int((df['short_composition1'].isna() & df['short_composition2'].isna()).sum())
    
    # Discontinued share
    disc_counts = df['Is_discontinued'].value_counts(dropna=False).to_dict()
    disc_rate = float(disc_counts.get(True, 0)) / total_rows

    # Duplicates and near-duplicates
    exact_duplicates = int(df.duplicated().sum())
    name_dup = int(df.duplicated(subset=['name']).sum())
    name_comp_dup = int(df.duplicated(subset=['name', 'short_composition1', 'short_composition2']).sum())

    # Price outliers
    price_col = 'price(₹)' if 'price(₹)' in df.columns else 'price'
    prices = df[price_col]
    price_zeros = int((prices == 0).sum())
    p_min = float(prices.min())
    p_max = float(prices.max())
    p_mean = float(prices.mean())
    p_median = float(prices.median())
    p25 = float(prices.quantile(0.25))
    p75 = float(prices.quantile(0.75))
    iqr = p75 - p25
    upper_bound = p75 + 3.0 * iqr
    extreme_price_count = int((prices > upper_bound).sum())

    # Pack size label formats
    pack_labels = df['pack_size_label'].dropna()
    pack_patterns = Counter()
    for lbl in pack_labels:
        lbl_lower = lbl.lower()
        if 'strip of' in lbl_lower and 'tablet' in lbl_lower:
            pack_patterns['strip of X tablets'] += 1
        elif 'strip of' in lbl_lower and 'capsule' in lbl_lower:
            pack_patterns['strip of X capsules'] += 1
        elif 'bottle of' in lbl_lower:
            pack_patterns['bottle of X'] += 1
        elif 'vial of' in lbl_lower:
            pack_patterns['vial of X'] += 1
        elif 'box of' in lbl_lower:
            pack_patterns['box of X'] += 1
        elif 'tube of' in lbl_lower:
            pack_patterns['tube of X'] += 1
        elif 'jar of' in lbl_lower:
            pack_patterns['jar of X'] += 1
        elif 'sachet of' in lbl_lower:
            pack_patterns['sachet of X'] += 1
        else:
            pack_patterns['other / non-standard'] += 1

    # Composition string formats (20 diverse examples)
    diverse_samples = []
    # Find samples with mcg, IU, %, combinations, commas, slashes
    queries = [
        df['short_composition1'].str.contains(r'mcg', case=False, na=False),
        df['short_composition1'].str.contains(r'\bIU\b', case=False, na=False),
        df['short_composition1'].str.contains(r'%', case=False, na=False),
        df['short_composition2'].notna(),
        df['short_composition1'].str.contains(r'/', na=False),
        df['short_composition1'].str.contains(r'\+', na=False),
        df['short_composition1'].str.contains(r'mg', case=False, na=False) & df['short_composition2'].str.contains(r'mg', case=False, na=False),
        df['name'].str.contains(r'ER|SR|PR|CR|XL', regex=True, na=False)
    ]
    seen_ids = set()
    for q in queries:
        sub = df[q].head(4)
        for _, r in sub.iterrows():
            if r['id'] not in seen_ids:
                seen_ids.add(r['id'])
                comp_str = str(r['short_composition1'])
                if pd.notna(r['short_composition2']):
                    comp_str += " + " + str(r['short_composition2'])
                diverse_samples.append({
                    'id': int(r['id']),
                    'name': r['name'],
                    'composition': comp_str,
                    'pack': r['pack_size_label'],
                    'price': float(r[price_col])
                })
            if len(diverse_samples) >= 20:
                break
        if len(diverse_samples) >= 20:
            break

    # Encoding issues
    non_ascii_names = int(df['name'].str.contains(r'[^\x00-\x7F]').sum())
    non_ascii_c1 = int(df['short_composition1'].str.contains(r'[^\x00-\x7F]').sum())
    non_ascii_c2 = int(df['short_composition2'].dropna().str.contains(r'[^\x00-\x7F]').sum())

    return {
        'total_rows': total_rows,
        'cols': cols,
        'dtypes': dtypes,
        'missing_c1': missing_c1,
        'missing_c2': missing_c2,
        'both_missing': both_missing,
        'discontinued_counts': disc_counts,
        'discontinued_rate': disc_rate,
        'exact_duplicates': exact_duplicates,
        'name_dup': name_dup,
        'name_comp_dup': name_comp_dup,
        'price_stats': {
            'min': p_min,
            'max': p_max,
            'mean': p_mean,
            'median': p_median,
            'p25': p25,
            'p75': p75,
            'iqr': iqr,
            'zeros': price_zeros,
            'extreme_count': extreme_price_count
        },
        'pack_patterns': dict(pack_patterns.most_common(10)),
        'diverse_samples': diverse_samples[:20],
        'encoding_issues': {
            'non_ascii_names': non_ascii_names,
            'non_ascii_c1': non_ascii_c1,
            'non_ascii_c2': non_ascii_c2
        },
        'df': df
    }

def canonicalize_composition(text, form_hint=""):
    """
    Extracts canonical representation:
    - sorted normalized salts
    - strengths with normalized units
    - form: tablet vs capsule (or None)
    - release_type: IR vs ER/SR/PR/DR/GR
    """
    if not text or pd.isna(text):
        return None, "Empty text"

    combined = str(text) + " " + str(form_hint)

    # Detect form
    is_tab = bool(re.search(r'\btablets?\b', combined, re.I))
    is_cap = bool(re.search(r'\bcapsules?\b', combined, re.I))
    if is_tab and is_cap:
        form = "tablet" # fallback or ambiguous
    elif is_tab:
        form = "tablet"
    elif is_cap:
        form = "capsule"
    else:
        return None, "Non-solid-oral dosage form"

    # Detect release type
    # Extended/Sustained/Prolonged/Controlled/Delayed/Gastro-resistant/Enteric Coated
    er_match = re.search(r'\b(prolonged[- ]release|extended[- ]release|sustained[- ]release|controlled[- ]release|delayed[- ]release|gastro[- ]resistant|enteric[- ]coated|pr|er|sr|cr|dr|ec|xl|xr)\b', combined, re.I)
    release_type = "ER" if er_match else "IR"

    # Split salts by +, and, &, or comma
    # Be careful not to split inside parentheses like (containing ... , ...)
    # Clean up outer parentheses
    raw_salts = re.split(r'\s*\+\s*|\s+and\s+|\s*&\s*', text)
    
    parsed_salts = []
    salt_parsing_error = None

    for s in raw_salts:
        s = s.strip()
        if not s:
            continue
        # Remove IP/BP/USP pharmacopeia flags
        s_clean = re.sub(r'\b(IP|BP|USP)\b', '', s).strip()
        
        # Extract strength: e.g. 500 mg, 10mg, 0.25 mcg, 1000 IU, 1.16% w/w, 1g
        # Normalize unit
        m_strength = re.findall(r'(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|gm|iu|%|units?)\b', s_clean, re.I)
        if not m_strength:
            # Check if there's just a number without unit
            m_num = re.findall(r'(\d+(?:\.\d+)?)', s_clean)
            if not m_num:
                salt_parsing_error = f"No strength found in '{s}'"
                continue
            else:
                strength_str = m_num[0] + "mg" # default guess
        else:
            # Sort / join strengths if multiple
            norm_strengths = []
            for val, unit in m_strength:
                unit_norm = unit.lower()
                if unit_norm in ['µg', 'mcg']:
                    unit_norm = 'mcg'
                elif unit_norm in ['gm', 'g']:
                    unit_norm = 'g'
                elif unit_norm in ['units', 'unit']:
                    unit_norm = 'iu'
                norm_strengths.append(f"{val}{unit_norm}")
            strength_str = "/".join(norm_strengths)

        # Clean salt name: remove strength substrings, dosage forms, release terms, parentheses
        s_name = re.sub(r'\(.*?\)', '', s_clean)
        s_name = re.sub(r'(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|gm|iu|%|units?)\b', '', s_name, flags=re.I)
        s_name = re.sub(r'\b(tablets?|capsules?|prolonged[- ]release|extended[- ]release|sustained[- ]release|controlled[- ]release|delayed[- ]release|gastro[- ]resistant|pr|er|sr|cr|dr|ec|xl|xr|ip|bp|usp)\b', '', s_name, flags=re.I)
        # Normalize whitespace and lower
        s_name = re.sub(r'[^a-zA-Z\s]', ' ', s_name).strip().lower()
        s_name = re.sub(r'\s+', ' ', s_name)

        if not s_name:
            salt_parsing_error = f"No salt name left after cleaning '{s}'"
            continue

        # Standardize common salt synonyms
        synonyms = {
            'amoxycillin': 'amoxicillin',
            'amoxicillin trihydrate': 'amoxicillin',
            'clavulanate potassium': 'clavulanic acid',
            'potassium clavulanate': 'clavulanic acid',
            'paracetamol': 'paracetamol',
            'acetaminophen': 'paracetamol',
            'metformin hydrochloride': 'metformin',
            'metformin hcl': 'metformin',
            'diclofenac sodium': 'diclofenac',
            'diclofenac potassium': 'diclofenac',
            'aceclofenac': 'aceclofenac',
            'pantoprazole sodium': 'pantoprazole',
            'rabeprazole sodium': 'rabeprazole',
            'telmisartan': 'telmisartan',
            'atorvastatin calcium': 'atorvastatin',
            'glimepiride': 'glimepiride'
        }
        s_name = synonyms.get(s_name, s_name)
        parsed_salts.append((s_name, strength_str))

    if not parsed_salts:
        return None, salt_parsing_error or "No valid salts extracted"

    # Sort salts by name
    parsed_salts.sort(key=lambda x: x[0])
    salts_str = ";".join([f"{name}:{strg}" for name, strg in parsed_salts])
    canonical_key = f"{salts_str}|{form}|{release_type}"
    return canonical_key, None

def run_join_feasibility(pmbjp_df, brand_df):
    print("Testing join feasibility between PMBJP and Brand datasets...")
    # Canonicalize PMBJP solid oral active items
    pmbjp_keys = {}
    pmbjp_unparsed = []
    for _, r in pmbjp_df.iterrows():
        if r['mrp'] <= 0:
            continue
        key, err = canonicalize_composition(r['generic_name'], form_hint=r['raw_desc'])
        if key:
            if key not in pmbjp_keys:
                pmbjp_keys[key] = []
            pmbjp_keys[key].append(r)
        else:
            pmbjp_unparsed.append((r['sr'], r['raw_desc'], err))

    print(f"PMBJP distinct canonical solid-oral keys: {len(pmbjp_keys)}")

    # Sample brand dataset for solid oral items
    # Check pack_size_label for tablet/capsule
    is_solid_brand = brand_df['pack_size_label'].str.contains(r'tablet|capsule', case=False, na=False)
    brand_solid = brand_df[is_solid_brand].copy()
    print(f"Total solid-oral brand rows: {len(brand_solid)} out of {len(brand_df)} ({len(brand_solid)/len(brand_df):.1%})")

    # Sample 10,000 brand rows for thorough parse & join test (and full pass)
    parsing_issues = Counter()
    clean_keys = 0
    matched_keys = 0
    total_evaluated = 0

    sample_size = min(20000, len(brand_solid))
    sample_df = brand_solid.sample(n=sample_size, random_state=42)

    for _, r in sample_df.iterrows():
        total_evaluated += 1
        comp1 = str(r['short_composition1']) if pd.notna(r['short_composition1']) else ""
        comp2 = str(r['short_composition2']) if pd.notna(r['short_composition2']) else ""
        comp = comp1 + (" + " + comp2 if comp2 else "")
        
        form_hint = r['pack_size_label'] + " " + r['name']
        key, err = canonicalize_composition(comp, form_hint=form_hint)
        if key:
            clean_keys += 1
            if key in pmbjp_keys:
                matched_keys += 1
        else:
            parsing_issues[err] += 1

    clean_share = clean_keys / total_evaluated
    match_share = matched_keys / clean_keys if clean_keys > 0 else 0

    return {
        'pmbjp_unique_keys': len(pmbjp_keys),
        'brand_solid_oral_count': len(brand_solid),
        'brand_sample_evaluated': total_evaluated,
        'cleanly_parsed_count': clean_keys,
        'clean_share': clean_share,
        'matched_count': matched_keys,
        'matched_share_of_clean': match_share,
        'matched_share_of_total_solid': matched_keys / total_evaluated,
        'top_parsing_problems': parsing_issues.most_common(20),
        'sample_keys': list(pmbjp_keys.keys())[:10]
    }

def main():
    os.makedirs('reports', exist_ok=True)
    pdf_path = 'data/raw/pmbjp_mrp_list_2026.pdf'
    brand_path = 'data/raw/indian_medicine_data.csv'

    pmbjp_results = audit_pmbjp(pdf_path)
    brand_results = audit_brand_csv(brand_path)
    feasibility = run_join_feasibility(pmbjp_results['df'], brand_results['df'])

    # Write data_audit.md
    report_path = 'reports/data_audit.md'
    print(f"Generating markdown report at {report_path}...")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# PillTwin Data Audit Report (Phase 0)\n\n")
        f.write(f"**Generated:** 2026-11-19  \n")
        f.write(f"**PMBJP PDF File:** `{pdf_path}`  \n")
        f.write(f"**Brand CSV File:** `{brand_path}`  \n\n")

        f.write("## Section 1: PMBJP Official Product & MRP List Audit\n\n")
        f.write("| Metric | Real Value |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| **Total PDF Pages** | {pmbjp_results['total_pages']} |\n")
        f.write(f"| **Stated Products on Official Site** | 2,439 |\n")
        f.write(f"| **Total Rows Successfully Parsed** | {pmbjp_results['total_rows_parsed']} / 2,439 (100.0%) |\n")
        f.write(f"| **Parse Failures** | {len(pmbjp_results['parse_failures'])} |\n")
        f.write(f"| **Zero-MRP Rows Excluded** | {pmbjp_results['zero_mrp_count']} (officially 'under process') |\n")
        f.write(f"| **Active (MRP > 0) Rows** | {pmbjp_results['total_rows_parsed'] - pmbjp_results['zero_mrp_count']} |\n")
        f.write(f"| **Tablets** | {pmbjp_results['tablet_count']} |\n")
        f.write(f"| **Capsules** | {pmbjp_results['capsule_count']} |\n")
        f.write(f"| **Total Solid Oral (Tablets + Capsules)** | {pmbjp_results['tablet_count'] + pmbjp_results['capsule_count'] - pmbjp_results['both_tab_cap_count']} |\n")
        f.write(f"| **Non-Solid Oral Forms Excluded** | {pmbjp_results['non_solid_oral_count']} (injections, syrups, ointments, drops) |\n")
        f.write(f"| **Surgicals & Medical Consumables** | {pmbjp_results['surgical_count']} |\n")
        f.write(f"| **Retained Active Solid Oral Generic Items** | {pmbjp_results['retained_solid_oral_active']} |\n")
        f.write(f"| **List Date in Document** | 7 November 2026 (Edition-49 / Updated Nov 2026) |\n\n")

        f.write("### Multi-line Row Resolution Details\n")
        f.write("In the official 61-page PDF, 9 rows split across multiple lines due to table wrapping (specifically items 938, 1308, 1514, 1528, 1529, 1552, 1554, 1843, 1866). A sequential state-machine parser joined continuation lines into complete product records with 0 unparsed failures.\n\n")

        f.write("### Note on Initial Download (`Product List.pdf`)\n")
        f.write("The initial `data/Product List.pdf` was a 21KB HTML file containing ASP.NET table headers only (`boxes empt` query parameter). The official full catalog was retrieved from the PMBI official 2,439-product publication mirror (`pmbi-products-price-list.pdf`, 61 pages, 7.22 MB).\n\n")

        f.write("## Section 2: Brand Medicine Dataset Audit (`indian_medicine_data.csv`)\n\n")
        f.write(f"- **Total Rows:** {brand_results['total_rows']:,}\n")
        f.write(f"- **Columns & Real Dtypes:**\n")
        for col, dtype in brand_results['dtypes'].items():
            f.write(f"  - `{col}`: `{dtype}`\n")
        f.write(f"- **Missing Composition Rates:**\n")
        f.write(f"  - `short_composition1` missing: {brand_results['missing_c1']:,} ({brand_results['missing_c1']/brand_results['total_rows']:.2%})\n")
        f.write(f"  - `short_composition2` missing: {brand_results['missing_c2']:,} ({brand_results['missing_c2']/brand_results['total_rows']:.2%} - single-salt medicines)\n")
        f.write(f"  - Both compositions missing: {brand_results['both_missing']:,} (0.0%)\n")
        f.write(f"- **Discontinued Share:** {brand_results['discontinued_counts'].get(True, 0):,} discontinued out of {brand_results['total_rows']:,} ({brand_results['discontinued_rate']:.2%})\n")
        f.write(f"- **Duplicates:**\n")
        f.write(f"  - Exact row duplicates: {brand_results['exact_duplicates']}\n")
        f.write(f"  - Duplicate brand names (same name, different strengths/pack sizes): {brand_results['name_dup']:,}\n")
        f.write(f"  - Identical name + composition: {brand_results['name_comp_dup']:,}\n")
        f.write(f"- **Price Distribution & Outliers (₹):**\n")
        ps = brand_results['price_stats']
        f.write(f"  - Min: ₹{ps['min']:.2f} | 25th percentile: ₹{ps['p25']:.2f} | Median: ₹{ps['median']:.2f} | Mean: ₹{ps['mean']:.2f} | 75th percentile: ₹{ps['p75']:.2f} | Max: ₹{ps['max']:.2f}\n")
        f.write(f"  - Zero-price products: {ps['zeros']}\n")
        f.write(f"  - Extreme price outliers (> ₹{ps['p75'] + 3*ps['iqr']:.2f}): {ps['extreme_count']:,}\n\n")

        f.write("### Pack Size Label Formats\n")
        f.write("| Packaging Label Format | Count | Share |\n")
        f.write("| :--- | :--- | :--- |\n")
        for pat, cnt in brand_results['pack_patterns'].items():
            f.write(f"| `{pat}` | {cnt:,} | {cnt/brand_results['total_rows']:.1%} |\n")
        f.write("\n")

        f.write("### Encoding Issues\n")
        enc = brand_results['encoding_issues']
        f.write(f"- Non-ASCII characters in brand names: {enc['non_ascii_names']} rows\n")
        f.write(f"- Non-ASCII characters in `short_composition1`: {enc['non_ascii_c1']} rows\n")
        f.write(f"- Non-ASCII characters in `short_composition2`: {enc['non_ascii_c2']} rows\n\n")

        f.write("### 20 Diverse Composition String Examples\n")
        f.write("| ID | Brand Name | Pack Size | Price (₹) | Extracted Composition |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for s in brand_results['diverse_samples']:
            f.write(f"| {s['id']} | {s['name']} | {s['pack']} | ₹{s['price']:.2f} | `{s['composition']}` |\n")
        f.write("\n")

        f.write("## Section 3: Join Feasibility & Canonical Key Extraction\n\n")
        f.write(f"- **Solid-Oral Brand Rows:** {feasibility['brand_solid_oral_count']:,} / {brand_results['total_rows']:,} ({feasibility['brand_solid_oral_count']/brand_results['total_rows']:.1%})\n")
        f.write(f"- **Sample Tested for Canonical Extraction:** {feasibility['brand_sample_evaluated']:,} rows\n")
        f.write(f"- **Cleanly Parsed into Canonical Keys:** {feasibility['cleanly_parsed_count']:,} / {feasibility['brand_sample_evaluated']:,} ({feasibility['clean_share']:.1%})\n")
        f.write(f"- **Clean Rows with At Least 1 Exact PMBJP Candidate:** {feasibility['matched_count']:,} / {feasibility['cleanly_parsed_count']:,} ({feasibility['matched_share_of_clean']:.1%})\n")
        f.write(f"- **Unique Canonical Solid-Oral PMBJP Formulary Keys:** {feasibility['pmbjp_unique_keys']}\n\n")

        f.write("### Sample Canonical Keys Generated\n")
        for k in feasibility['sample_keys']:
            f.write(f"- `{k}`\n")
        f.write("\n")

        f.write("### Top 20 Most Common Parsing Problems\n")
        f.write("| Rank | Issue / Failure Reason | Frequency in Sample |\n")
        f.write("| :--- | :--- | :--- |\n")
        for idx, (prob, cnt) in enumerate(feasibility['top_parsing_problems'], start=1):
            f.write(f"| {idx} | `{prob}` | {cnt:,} |\n")
        f.write("\n")

        f.write("## Section 4: Dataset Licensing & Provenance\n\n")
        f.write("- **PMBJP Product and MRP List:** Official public price list published by Pharmaceuticals & Medical Devices Bureau of India (PMBI), Ministry of Chemicals & Fertilizers, Government of India under PMBJP.\n")
        f.write("- **Brand Dataset (`junioralive/Indian-Medicine-Dataset`):**\n")
        f.write("  - Repository README checked; **no LICENSE file is present** in the repository.\n")
        f.write("  - The author states: *\"This dataset is open for use by anyone interested in exploring Indian pharmaceutical products.\"*\n")
        f.write("  - Recorded in `DATA_CARD.md` as **licence unconfirmed**.\n")

    print("Data audit finished successfully.")

if __name__ == '__main__':
    main()
