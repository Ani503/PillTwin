import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# Explicit whitelist of equivalent active salt pairs.
# Unknown or non-whitelisted salts are NOT modified and must NOT exact-match.
# Suffixes like valerate, propionate, acetate, phosphate, sulphate, nitrate, fumarate are NOT stripped by default.
SALT_EQUIVALENT_WHITELIST = {
    # Antibiotics / Penicillins
    'amoxycillin': 'amoxicillin',
    'amoxicillin trihydrate': 'amoxicillin',
    'amoxycillin trihydrate': 'amoxicillin',
    'clavulanate potassium': 'clavulanic acid',
    'potassium clavulanate': 'clavulanic acid',
    'clavulanate': 'clavulanic acid',
    'ampicillin sodium': 'ampicillin',
    'ampicillin trihydrate': 'ampicillin',
    'cloxacillin sodium': 'cloxacillin',
    'ciprofloxacin hydrochloride': 'ciprofloxacin',
    'ciprofloxacin hcl': 'ciprofloxacin',
    'levofloxacin hemihydrate': 'levofloxacin',
    'doxycycline hyclate': 'doxycycline',
    'doxycycline monohydrate': 'doxycycline',
    'azithromycin dihydrate': 'azithromycin',
    'cefixime trihydrate': 'cefixime',
    
    # Analgesics / Antipyretics / NSAIDs
    'paracetamol': 'paracetamol',
    'acetaminophen': 'paracetamol',
    'aceclofenac': 'aceclofenac',
    'ibuprofen': 'ibuprofen',
    'ketorolac tromethamine': 'ketorolac',
    'nimesulide': 'nimesulide',
    'tramadol hydrochloride': 'tramadol',
    'tramadol hcl': 'tramadol',
    'etoricoxib': 'etoricoxib',
    'aspirin': 'aspirin',
    'acetylsalicylic acid': 'aspirin',
    
    # Cardiovascular & Antihypertensives
    'amlodipine besylate': 'amlodipine',
    'amlodipine besilate': 'amlodipine',
    'amlodipine maleate': 'amlodipine',
    'telmisartan': 'telmisartan',
    'losartan potassium': 'losartan',
    'olmesartan medoxomil': 'olmesartan',
    'valsartan': 'valsartan',
    'atorvastatin calcium': 'atorvastatin',
    'rosuvastatin calcium': 'rosuvastatin',
    'simvastatin': 'simvastatin',
    'atenolol': 'atenolol',
    'carvedilol': 'carvedilol',
    'nebivolol hydrochloride': 'nebivolol',
    'nebivolol hcl': 'nebivolol',
    'ramipril': 'ramipril',
    'enalapril maleate': 'enalapril',
    'hydrochlorothiazide': 'hydrochlorothiazide',
    'chlorthalidone': 'chlorthalidone',
    'indapamide': 'indapamide',
    'bisoprolol fumarate': 'bisoprolol',
    'quetiapine fumarate': 'quetiapine',
    
    # Anti-Diabetic
    'metformin hydrochloride': 'metformin',
    'metformin hcl': 'metformin',
    'glimepiride': 'glimepiride',
    'gliclazide': 'gliclazide',
    'glipizide': 'glipizide',
    'vildagliptin': 'vildagliptin',
    'sitagliptin phosphate': 'sitagliptin',
    'linagliptin': 'linagliptin',
    'teneligliptin hydrobromide hydrate': 'teneligliptin',
    'dapagliflozin propanediol': 'dapagliflozin',
    'empagliflozin': 'empagliflozin',
    'voglibose': 'voglibose',
    'pioglitazone hydrochloride': 'pioglitazone',
    'pioglitazone hcl': 'pioglitazone',
    
    # Gastrointestinal
    'pantoprazole sodium': 'pantoprazole',
    'pantoprazole sodium sesquihydrate': 'pantoprazole',
    'rabeprazole sodium': 'rabeprazole',
    'omeprazole magnesium': 'omeprazole',
    'esomeprazole magnesium': 'esomeprazole',
    'domperidone maleate': 'domperidone',
    'ondansetron hydrochloride': 'ondansetron',
    'ondansetron hcl': 'ondansetron',
    'ranitidine hydrochloride': 'ranitidine',
    'ranitidine hcl': 'ranitidine',
    
    # Antihistamines & Respiratory
    'levocetirizine dihydrochloride': 'levocetirizine',
    'levocetirizine hydrochloride': 'levocetirizine',
    'levocetirizine hcl': 'levocetirizine',
    'cetirizine dihydrochloride': 'cetirizine',
    'cetirizine hydrochloride': 'cetirizine',
    'cetirizine hcl': 'cetirizine',
    'montelukast sodium': 'montelukast',
    'fexofenadine hydrochloride': 'fexofenadine',
    'fexofenadine hcl': 'fexofenadine',
    'bilastine': 'bilastine',
    'chlorpheniramine maleate': 'chlorpheniramine',
    'hydroxyzine hydrochloride': 'hydroxyzine',
    
    # Vitamins & Minerals
    'folic acid': 'folic acid',
    'folate': 'folic acid',
    'mecobalamin': 'methylcobalamin',
    'cyanocobalamin': 'vitamin b12',
    'vitamin d3': 'cholecalciferol',
    'ascorbic acid': 'vitamin c',
    'calcium carbonate': 'calcium carbonate',
    'calcitriol': 'calcitriol',
}

# Delivery and packaging tokens to strip from salt names (whole tokens only, no salt/ester stripping)
DELIVERY_FORMAT_TOKENS = [
    r'\btablets?\b', r'\bcapsules?\b', r'\btabs?\b', r'\bcaps?\b',
    r'\b\d+[\'’]s\b', # e.g. 60's, 10's in name
    r'\b(ip|bp|usp)\b',
    r'\bprolonged[- ]release\b', r'\bextended[- ]release\b', r'\bsustained[- ]release\b',
    r'\bcontrolled[- ]release\b', r'\bdelayed[- ]release\b', r'\bgastro[- ]resist\w*\b',
    r'\benteric[- ]coated\b', r'\bdispersible\b', r'\bchewable\b', r'\bmouth[- ]dissolving\b',
    r'\beffervescent\b'
]

NON_SOLID_ORAL_PATTERNS = [
    r'\binjection\b', r'\binj\b', r'\bvial\b', r'\bampoule\b', r'\biv fluid\b',
    r'\bsyrup\b', r'\bsuspension\b', r'\bliquid\b', r'\bsoln\b', r'\bsolution\b',
    r'\bcream\b', r'\bgel\b', r'\bointment\b', r'\blotion\b', r'\bdrops?\b',
    r'\beye drops?\b', r'\bear drops?\b', r'\bnasal spray\b', r'\binhaler\b',
    r'\brespule\b', r'\bpowder\b', r'\bdusting powder\b', r'\bsachet\b',
    r'\bshampoo\b', r'\bwash\b', r'\bgargle\b', r'\bmouthwash\b', r'\bsoap\b',
    r'\btoothpaste\b', r'\bdevice\b', r'\bbandage\b', r'\bcannula\b', r'\bgloves\b',
    r'\bsyringe\b', r'\bneedle\b', r'\bcatheter\b', r'\btape\b', r'\bmask\b'
]

@dataclass
class CanonicalProduct:
    salts: List[Tuple[str, str]]  # list of (normalized_salt_name, normalized_strength)
    dosage_form: Optional[str]    # 'tablet' or 'capsule'
    release_type: str             # 'IR', 'ER', 'DR', or combined e.g. 'DR+ER'
    release_type_source: str      # 'stated' or 'assumed'
    release_type_note: Optional[str] # "assumed immediate-release, not stated in source" if assumed
    canonical_key: Optional[str]  # e.g., 'amoxicillin:500mg;clavulanic acid:125mg|tablet|IR'
    is_solid_oral: bool
    raw_text: str
    error: Optional[str] = None
    component_releases: Optional[List[Dict[str, str]]] = None

def normalize_salt_name(raw_name: str) -> str:
    """
    Cleans and standardizes an active salt ingredient name.
    Uses whole-token matching only (never substring).
    Does NOT strip valerate, propionate, acetate, phosphate, sulphate, nitrate, fumarate.
    Maps to equivalent only if explicitly present in SALT_EQUIVALENT_WHITELIST.
    """
    s = raw_name.lower().strip()
    # Remove text inside parentheses (e.g., "(as ampicillin sodium)" or leftover strength)
    s = re.sub(r'\(.*?\)', '', s)
    # Strip strength tokens if leftover (whole tokens only)
    s = re.sub(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|gm|iu|%|units?)\b', '', s, flags=re.I)
    
    # Strip delivery and packaging format tokens (whole tokens only)
    for pat in DELIVERY_FORMAT_TOKENS:
        s = re.sub(pat, '', s, flags=re.I)

    # Normalize punctuation and whitespace
    s = re.sub(r'[^a-z0-9\s-]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Whole-token spelling normalization: sulfate -> sulphate
    s = re.sub(r'\bsulfate\b', 'sulphate', s)

    # Check explicit equivalent whitelist
    if s in SALT_EQUIVALENT_WHITELIST:
        s = SALT_EQUIVALENT_WHITELIST[s]
    return s

def normalize_strength(val_str: str, unit_str: str) -> str:
    """Normalizes strength numbers and units into standard forms."""
    try:
        val = float(val_str)
    except ValueError:
        return f"{val_str}{unit_str.lower()}"

    unit = unit_str.lower()
    
    # Convert grams to mg for consistency (e.g., 1g -> 1000mg, 0.5g -> 500mg)
    if unit in ['g', 'gm']:
        val = val * 1000.0
        unit = 'mg'
    elif unit in ['mcg', 'µg', 'ug']:
        unit = 'mcg'
    elif unit in ['iu', 'units', 'unit', 'million iu', 'miu']:
        unit = 'iu'
    elif unit in ['%']:
        unit = '%'

    # Remove trailing zeroes from float (e.g. 500.0 -> 500, 0.5 -> 0.5)
    if val.is_integer():
        formatted_val = f"{int(val)}"
    else:
        formatted_val = f"{val:g}"

    return f"{formatted_val}{unit}"

def parse_composition(text: str, form_hint: str = "", name_hint: str = "") -> CanonicalProduct:
    """
    Parses medicine composition string and contextual form hints into a canonical key.
    Enforces Rule 1: Exact match requires identical sorted salts, identical strengths with units,
    identical dosage form (tablet vs capsule), and identical release type (IR vs ER vs DR).
    """
    if not text or not str(text).strip():
        return CanonicalProduct([], None, "IR", "assumed", "assumed immediate-release, not stated in source", None, False, text, "Empty composition string")

    full_context = f"{text} {form_hint} {name_hint}".lower()

    # Check for explicitly unsupported / non-solid-oral formulations
    for pat in NON_SOLID_ORAL_PATTERNS:
        if re.search(pat, full_context):
            # Exception: if context also says tablet/capsule, verify if it's oral solid
            # e.g. "Paracetamol Oral Suspension" is non-solid; "Paracetamol Tablets" is solid.
            if not re.search(r'\b(tablets?|capsules?)\b', full_context):
                return CanonicalProduct([], None, "IR", "assumed", "assumed immediate-release, not stated in source", None, False, text, f"Non-solid-oral form detected: pattern '{pat}'")

    # Detect dosage form (Tablets vs Capsules only in Scope v1, distinguishing specialized forms)
    is_tab = bool(re.search(r'\b(tablets?|tab|tabs)\b', full_context))
    is_cap = bool(re.search(r'\b(capsules?|cap|caps)\b', full_context))

    # Specialized physical delivery characteristics
    is_dispersible = bool(re.search(r'\b(dispersible|dt)\b', full_context))
    is_effervescent = bool(re.search(r'\beffervescent\b', full_context))
    is_chewable = bool(re.search(r'\bchewable\b', full_context))
    is_mouth_dissolving = bool(re.search(r'\b(mouth[- ]dissolving|md|odt)\b', full_context))
    is_softgel = bool(re.search(r'\b(soft[- ]gelatin|softgel)\b', full_context))

    base_form = None
    if is_tab and is_cap:
        # Check primary emphasis
        if re.search(r'\btablets?\b', form_hint.lower()) or re.search(r'\btablets?\b', name_hint.lower()):
            base_form = "tablet"
        elif re.search(r'\bcapsules?\b', form_hint.lower()) or re.search(r'\bcapsules?\b', name_hint.lower()):
            base_form = "capsule"
        else:
            base_form = "tablet"
    elif is_tab:
        base_form = "tablet"
    elif is_cap:
        base_form = "capsule"
    else:
        return CanonicalProduct([], None, "IR", "assumed", "assumed immediate-release, not stated in source", None, False, text, "No solid oral dosage form (tablet/capsule) identified")

    if base_form == "tablet":
        if is_dispersible:
            dosage_form = "tablet_dispersible"
        elif is_effervescent:
            dosage_form = "tablet_effervescent"
        elif is_chewable:
            dosage_form = "tablet_chewable"
        elif is_mouth_dissolving:
            dosage_form = "tablet_mouth_dissolving"
        else:
            dosage_form = "tablet"
    else:
        if is_softgel:
            dosage_form = "capsule_softgel"
        else:
            dosage_form = "capsule"

    # Detect release type: Immediate (IR) vs Delayed Release / Gastro-Resistant (DR) vs Extended / Sustained (ER)
    dr_match = bool(re.search(r'\b(delayed[- ]release|gastro[- ]resist\w*|enteric[- ]coated|dr|ec|dsr)\b', full_context))
    er_match = bool(re.search(r'\b(prolonged[- ]release|extended[- ]release|sustained[- ]release|controlled[- ]release|pr|er|sr|cr|xl|xr|mr)\b', full_context))
    ir_match = bool(re.search(r'\b(immediate[- ]release|ir)\b', full_context))

    if dr_match:
        release_type = "DR"
        release_type_source = "stated"
        release_type_note = None
    elif er_match:
        release_type = "ER"
        release_type_source = "stated"
        release_type_note = None
    else:
        release_type = "IR"
        if ir_match:
            release_type_source = "stated"
            release_type_note = None
        else:
            release_type_source = "assumed"
            release_type_note = "assumed immediate-release, not stated in source"

    # Split salts: delimiters +, and, &, or commas (outside parentheses)
    # First, handle parentheses safely
    raw_segments = re.split(r'\s*\+\s*|\s+and\s+|\s*&\s*|,\s*', text)
    
    parsed_components = []
    
    for seg in raw_segments:
        seg = seg.strip()
        if not seg:
            continue
        
        # Check if segment has strength (e.g., 500mg, 10 mg, 0.25mcg, 1000 IU, 1g)
        strengths = re.findall(r'(\d+(?:\.\d+)?)\s*(mg|mcg|µg|ug|g|gm|iu|%|units?)\b', seg, flags=re.I)
        
        if not strengths:
            # Fallback check for numbers in parentheses or alone
            m_num = re.findall(r'\((\d+(?:\.\d+)?)\)', seg)
            if m_num:
                norm_str = f"{m_num[0]}mg"
            else:
                return CanonicalProduct([], dosage_form, release_type, release_type_source, release_type_note, None, True, text, f"Missing strength in salt segment '{seg}'")
        else:
            norm_str_list = [normalize_strength(val, unit) for val, unit in strengths]
            norm_str = "/".join(norm_str_list)

        salt_name = normalize_salt_name(seg)
        if not salt_name:
            return CanonicalProduct([], dosage_form, release_type, release_type_source, release_type_note, None, True, text, f"Unable to extract salt name from '{seg}'")

        # Component-level release detection
        seg_lower = seg.lower()
        dr_seg = bool(re.search(r'\b(delayed[- ]release|gastro[- ]resist\w*|enteric[- ]coated|dr|ec)\b', seg_lower))
        er_seg = bool(re.search(r'\b(prolonged[- ]release|extended[- ]release|sustained[- ]release|controlled[- ]release|pr|er|sr|cr|xl|xr|mr)\b', seg_lower))
        ir_seg = bool(re.search(r'\b(immediate[- ]release|ir)\b', seg_lower))

        if dr_seg:
            comp_rel = "DR"
            comp_src = "stated"
        elif er_seg:
            comp_rel = "ER"
            comp_src = "stated"
        elif ir_seg:
            comp_rel = "IR"
            comp_src = "stated"
        else:
            # Check context: if DSR or EC+SR is in context, PPI is DR, prokinetic is ER
            if bool(re.search(r'\b(dsr|ec\s*\+\s*sr)\b', full_context)):
                if any(ppi in salt_name for ppi in ['rabeprazole', 'pantoprazole', 'esomeprazole', 'omeprazole', 'ilaprazole']):
                    comp_rel = "DR"
                    comp_src = "stated"
                elif any(pro in salt_name for pro in ['domperidone', 'levosulpiride', 'itopride', 'cinitapride']):
                    comp_rel = "ER"
                    comp_src = "stated"
                else:
                    comp_rel = release_type
                    comp_src = release_type_source
            else:
                comp_rel = release_type
                comp_src = release_type_source

        parsed_components.append((salt_name, norm_str, comp_rel, comp_src))

    if not parsed_components:
        return CanonicalProduct([], dosage_form, release_type, release_type_source, release_type_note, None, True, text, "No valid salts extracted")

    # Sort components alphabetically by normalized name (Rule 1: normalised salt set order)
    parsed_components.sort(key=lambda x: x[0])
    parsed_salts = [(c[0], c[1]) for c in parsed_components]
    comp_releases_list = [
        {'salt': c[0], 'strength': c[1], 'release_type': c[2], 'release_type_source': c[3]}
        for c in parsed_components
    ]

    unique_comp_releases = set(c[2] for c in parsed_components)
    if len(unique_comp_releases) > 1:
        # Multi-salt combination with different component release types (e.g. Rabeprazole DR + Domperidone ER)
        salts_repr = ";".join([f"{c[0]}:{c[1]}:{c[2]}" for c in parsed_components])
        canonical_key = f"{salts_repr}|{dosage_form}"
        overall_release_type = "+".join(sorted(unique_comp_releases))
        overall_release_source = "stated"
        overall_release_note = None
    else:
        salts_repr = ";".join([f"{c[0]}:{c[1]}" for c in parsed_components])
        overall_release_type = list(unique_comp_releases)[0] if unique_comp_releases else release_type
        canonical_key = f"{salts_repr}|{dosage_form}|{overall_release_type}"
        overall_release_source = parsed_components[0][3] if parsed_components else release_type_source
        overall_release_note = "assumed immediate-release, not stated in source" if overall_release_type == "IR" and overall_release_source == "assumed" else None

    return CanonicalProduct(
        salts=parsed_salts,
        dosage_form=dosage_form,
        release_type=overall_release_type,
        release_type_source=overall_release_source,
        release_type_note=overall_release_note,
        canonical_key=canonical_key,
        is_solid_oral=True,
        raw_text=text,
        error=None,
        component_releases=comp_releases_list
    )

def parse_pack_size(label: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parses package size labels into unit counts.
    e.g. 'strip of 10 tablets' -> (10, 'tablet')
         'strip of 15 capsules' -> (15, 'capsule')
         '10's' -> (10, 'units')
         '15's' -> (15, 'units')
    """
    if not label or not str(label).strip():
        return None, "Empty pack size label"

    lbl = str(label).strip().lower()

    # Pattern: strip of X tablets/capsules/units
    m_strip = re.search(r'strip\s+of\s+(\d+)\s*(tablets?|capsules?|pills?|units?)?', lbl)
    if m_strip:
        count = int(m_strip.group(1))
        unit = m_strip.group(2) or "units"
        return count, unit

    # Pattern: bottle/box/pack of X tablets/capsules
    m_box = re.search(r'(?:bottle|box|pack|strip)\s+of\s+(\d+)', lbl)
    if m_box:
        return int(m_box.group(1)), "units"

    # Pattern: 10's, 15's, 100's
    m_apostrophe = re.search(r'(\d+)[\'’]s', lbl)
    if m_apostrophe:
        return int(m_apostrophe.group(1)), "units"

    # Pattern: 10 tablets, 15 capsules
    m_count_type = re.search(r'^(\d+)\s*(?:tablets?|capsules?|tabs?|caps?|units?)', lbl)
    if m_count_type:
        return int(m_count_type.group(1)), "units"

    # Single number alone
    m_num_only = re.search(r'^\s*(\d+)\s*$', lbl)
    if m_num_only:
        return int(m_num_only.group(1)), "units"

    return None, f"Unrecognized pack size format: '{label}'"

def check_caution_drug(salts: List[Tuple[str, str]], caution_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Checks if any active salt in the parsed product belongs to the caution drugs list.
    """
    caution_list = caution_config.get('caution_drugs', [])
    flags = []
    
    salt_names = set(s[0].lower() for s in salts)
    
    for item in caution_list:
        synonyms = [syn.lower() for syn in item.get('synonyms', [])]
        synonyms.append(item.get('canonical_name', '').lower())
        
        # Check intersection
        for sn in salt_names:
            if any(syn in sn or sn in syn for syn in synonyms):
                flags.append({
                    'id': item['id'],
                    'matched_salt': sn,
                    'category': item['category'],
                    'reason': item['reason'],
                    'caution_message': item['caution_message']
                })
                break

    return flags
