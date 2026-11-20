import re
from typing import List, Optional, Tuple, Dict, Any

class NoiseLineFilter:
    """
    Filters non-medicine noise text lines commonly found on pharmaceutical packaging
    (batch numbers, expiry dates, manufacturing licenses, addresses, MRP, barcode artifacts).
    Retains candidate brand names, active ingredient compositions, and strengths.
    """

    # Patterns indicating non-medicine noise lines
    NOISE_PATTERNS = [
        # Batch and Lot numbers
        r'\b(?:b\.?no|batch\s*(?:no\.?|number)?|lot\s*(?:no\.?|number)?|b\/n|b\.\s*no)\b',
        # Manufacturing and Expiry dates
        r'\b(?:mfg\.?\s*(?:date|dt)?|exp\.?\s*(?:date|dt)?|mfd\.?|expiry\s*date|use\s*before|best\s*before)\b',
        # MRP and Pricing
        r'\b(?:m\.?r\.?p\.?|mrp|₹|rs\.?|incl\.?\s*of\s*all\s*taxes|max\.?\s*retail\s*price|per\s*strip|per\s*tab)\b',
        # Regulatory Licenses and Barcodes
        r'\b(?:mfg\.?\s*lic\.?\s*(?:no)?|licence\s*no|license\s*no|regd?\.?\s*off|gmp|who[- ]gmp|fssai|cin\b)\b',
        # Manufacturing / Marketing Corporate Details and Addresses
        r'\b(?:marketed\s*by|mkt\.?\s*by|manufactured\s*by|mfd\.?\s*by|packed\s*by|imported\s*by)\b',
        r'\b(?:pvt\.?\s*ltd\.?|private\s*limited|ltd\.?|inc\.?|corp\.?|pharma\s*labs?|laboratories|pharmaceuticals?)\b',
        r'\b(?:industrial\s*area|phase[- ]?\d+|plot\s*no|village|road|distt?\.?|pin\s*code|e[- ]?mail|website|www\.\w+)\b',
        # Storage Instructions & Warnings
        r'\b(?:store\s*(?:in|below|at)|cool\s*(?:&|and)\s*dry\s*place|protect\s*from\s*(?:light|moisture))\b',
        r'\b(?:keep\s*out\s*of\s*(?:the\s*)?reach\s*of\s*children|do\s*not\s*freeze|temperature\s*not\s*exceeding)\b',
        r'\b(?:dosage\s*:|as\s*directed\s*by\s*(?:the\s*)?physician|for\s*therapeutic\s*use\s*only)\b',
        # Prescription drug warnings and Schedules
        r'\b(?:schedule\s*[ghhx1]\s*(?:prescription)?\s*drug|caution\s*:|warning\s*:|to\s*be\s*sold\s*by\s*retail)\b',
        # Packaging specifications alone
        r'^\s*(?:strip\s*of\s*\d+\s*(?:tablets?|capsules?)|blister\s*pack|alu[- ]alu|foil)\s*$'
    ]

    # Pre-compiled regex patterns for speed
    _COMPILED_NOISE = [re.compile(p, re.I) for p in NOISE_PATTERNS]

    @classmethod
    def is_noise_line(cls, line: str) -> bool:
        """
        Determines whether a detected OCR line is packaging/manufacturing noise.
        """
        if not line or not str(line).strip():
            return True

        text = str(line).strip()

        # Reject lines that are too short (less than 3 characters) or purely punctuation
        if len(text) < 3 or not re.search(r'[a-zA-Z0-9]', text):
            return True

        # Reject lines consisting purely of numbers or dates (e.g. "05/2026", "123456")
        if re.match(r'^\s*[\d\s\/\.\-:,]+\s*$', text):
            return True

        # Check compiled noise patterns
        for pat in cls._COMPILED_NOISE:
            if pat.search(text):
                # Exception: if line explicitly has brand-like tokens or active salt with strength,
                # check if noise token is just an isolated suffix
                if re.search(r'\b(tablets?|capsules?)\b', text, re.I) and re.search(r'\d+\s*(?:mg|mcg|g)\b', text, re.I):
                    # Keep lines like "Dolo 650 Tablets (Mfg by Micro Labs)" but clean them
                    if not re.match(r'^\s*(?:marketed\s*by|mfg\s*by|batch|exp|mrp)', text, re.I):
                        return False
                return True

        return False

    @classmethod
    def clean_ocr_line(cls, line: str) -> str:
        """
        Cleans detected OCR line: normalizes whitespace, corrects frequent OCR
        character confusions in pharmaceutical context, and strips trailing garbage.
        """
        t = str(line).strip()

        # Fix frequent OCR character confusions in strength numbers:
        # e.g. "65O mg" -> "650 mg", "5OO mg" -> "500 mg"
        def _normalize_num_o(m):
            return re.sub(r'[Oo]', '0', m.group(1)) + m.group(2)
        t = re.sub(r'\b([0-9Oo]+(?:\.[0-9Oo]+)?)(\s*(?:mg|mcg|µg|g|gm|iu|%)\b)', _normalize_num_o, t)
        t = re.sub(r'\b(\d+)[Oo]+\b', lambda m: m.group(1) + '0' * (len(m.group(0)) - len(m.group(1))), t)
        t = re.sub(r'\b[Oo]+(\d+)\b', lambda m: '0' * (len(m.group(0)) - len(m.group(1))) + m.group(1), t)

        # Fix lowercase 'l' or uppercase 'I' confused with digit 1 in strength:
        # e.g. "l0 mg" -> "10 mg"
        t = re.sub(r'\b[lI](\d+)\s*(?:mg|mcg)\b', r'1\1 mg', t)

        # Remove surrounding punctuation quotes and brackets
        t = re.sub(r'^[^\w]+|[^\w]+$', '', t)
        t = re.sub(r'\s+', ' ', t).strip()

        return t

    @classmethod
    def filter_lines(cls, lines: List[str]) -> List[str]:
        """
        Filters and cleans a list of raw OCR text lines, returning deduplicated candidate lines.
        """
        candidates: List[str] = []
        seen = set()

        for raw_line in lines:
            cleaned = cls.clean_ocr_line(raw_line)
            if not cls.is_noise_line(cleaned):
                lower_key = cleaned.lower()
                if lower_key not in seen and len(cleaned) >= 3:
                    seen.add(lower_key)
                    candidates.append(cleaned)

        return candidates

    @classmethod
    def extract_strengths(cls, lines: List[str]) -> List[str]:
        """
        Extracts and normalizes all drug strength tokens (e.g. '650mg', '40mg', '0.5mg')
        found in the OCR text lines.
        """
        strengths = []
        seen = set()
        pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|gm|iu)\b', re.IGNORECASE)
        for line in lines:
            matches = pattern.findall(str(line))
            for val, unit in matches:
                u_norm = unit.lower()
                if u_norm in ('µg', 'mcg'):
                    norm_str = f"{float(val):g}mcg"
                elif u_norm in ('g', 'gm'):
                    norm_str = f"{float(val):g}g"
                else:
                    norm_str = f"{float(val):g}{u_norm}"
                if norm_str not in seen:
                    seen.add(norm_str)
                    strengths.append(norm_str)
        return strengths

    @classmethod
    def extract_cues(cls, lines: List[str]) -> Dict[str, List[str]]:
        """
        Extracts dosage form and release cues from the OCR text lines
        (e.g. DT, MD, effervescent, chewable, SR, ER, XR, DR, PR).
        """
        form_cues = []
        release_cues = []
        full_text = " ".join(lines).lower()

        # Dosage form cues
        if re.search(r'\b(dt|dispersible)\b', full_text):
            form_cues.append("DT")
        if re.search(r'\b(md|mouth[- ]dissolving)\b', full_text):
            form_cues.append("MD")
        if re.search(r'\beffervescent\b', full_text):
            form_cues.append("effervescent")
        if re.search(r'\bchewable\b', full_text):
            form_cues.append("chewable")
        if re.search(r'\b(tablets?|tabs?)\b', full_text):
            form_cues.append("tablet")
        if re.search(r'\b(capsules?|caps?)\b', full_text):
            form_cues.append("capsule")

        # Release characteristics cues
        if re.search(r'\b(dr|delayed[- ]release|gastro[- ]resistant|enteric[- ]coated|ec)\b', full_text):
            release_cues.append("DR")
        if re.search(r'\b(sr|sustained[- ]release)\b', full_text):
            release_cues.append("SR")
        if re.search(r'\b(er|extended[- ]release)\b', full_text):
            release_cues.append("ER")
        if re.search(r'\b(xr)\b', full_text):
            release_cues.append("XR")
        if re.search(r'\b(pr|prolonged[- ]release)\b', full_text):
            release_cues.append("PR")

        return {
            "form_cues": list(dict.fromkeys(form_cues)),
            "release_cues": list(dict.fromkeys(release_cues))
        }

    @classmethod
    def extract_brand_tokens(cls, lines: List[str]) -> List[str]:
        """
        Extracts candidate brand name tokens from cleaned candidate lines
        by removing pharmacopeial tokens (IP, BP, USP) and generic dosage trailers.
        """
        brand_tokens = []
        seen = set()

        for line in lines:
            t = cls.clean_ocr_line(line)
            if cls.is_noise_line(t):
                continue
            # Strip pharmacopeia marks and trailers
            cleaned = re.sub(r'\b(ip|bp|usp)\b', '', t, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b(tablets?|capsules?|tabs?|caps?)\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if len(cleaned) >= 3 and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                brand_tokens.append(cleaned)

        return brand_tokens
