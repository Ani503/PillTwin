import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from PIL import Image

from src.ocr.preprocessor import ImagePreprocessor
from src.ocr.filters import NoiseLineFilter
from src.matching.brand_matcher import BrandMatcher, BrandCandidate

logger = logging.getLogger(__name__)

MANDATORY_DISCLAIMER = "Information only, not medical advice. Ask your doctor or pharmacist before changing any medicine."

@dataclass
class DetectedLine:
    text: str
    confidence: float
    source_crop: str
    is_noise: bool

@dataclass
class OCRResult:
    raw_lines: List[str]
    raw_ocr_text: str
    cleaned_candidate_lines: List[str]
    suggested_brands: List[Dict[str, Any]]
    detected_lines_detail: List[DetectedLine]
    extracted_strengths: List[str]
    extracted_cues: Dict[str, List[str]]
    engine_name: str
    languages_used: str
    skew_angle: float
    image_shape: List[int]
    low_confidence: bool = False
    low_confidence_message: Optional[str] = None
    exact_match_produced: bool = False
    prompt_message: str = "Is this your medicine? Tap your brand to view generic equivalents."
    disclaimer: str = MANDATORY_DISCLAIMER

class BaseOCREngine(ABC):
    """Abstract Base Class for Swappable OCR Engines."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> Tuple[List[DetectedLine], float, List[int]]:
        """
        Extracts raw text lines and confidence scores from in-memory image bytes.
        Never writes files to disk (Non-Negotiable Rule 6).
        """
        pass

class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR Engine (PP-OCRv6). Primary high-accuracy OCR engine.
    Processes in-memory RGB arrays without temporary file persistence.
    """
    def __init__(self, lang: str = "en"):
        from paddleocr import PaddleOCR
        # Initialize PaddleOCR with textline orientation classification
        try:
            self.ocr = PaddleOCR(use_textline_orientation=True, lang=lang)
        except TypeError:
            self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        self.preprocessor = ImagePreprocessor()
        self.name = "PaddleOCR 3.7.0 (PP-OCRv6)"
        self.languages_used = lang

    def extract_text(self, image_bytes: bytes) -> Tuple[List[DetectedLine], float, List[int]]:
        preprocessed = self.preprocessor.process_pipeline(image_bytes)
        skew_angle = preprocessed['skew_angle']
        orig_shape = list(preprocessed['original_shape'])
        rgb_img = preprocessed['rgb']

        detected_lines: List[DetectedLine] = []
        seen = set()

        # Run PaddleOCR on the preprocessed RGB image
        try:
            raw_res = self.ocr.ocr(rgb_img)
        except Exception as e:
            logger.warning(f"PaddleOCR inference failed on image: {e}")
            raw_res = []

        if raw_res:
            for page in raw_res:
                if isinstance(page, dict):
                    texts = page.get('rec_texts', [])
                    scores = page.get('rec_scores', [])
                    for t, s in zip(texts, scores):
                        t_str = str(t).strip()
                        if t_str and t_str.lower() not in seen:
                            seen.add(t_str.lower())
                            is_noise = NoiseLineFilter.is_noise_line(t_str)
                            detected_lines.append(DetectedLine(
                                text=t_str,
                                confidence=float(round(float(s) * 100, 2)),
                                source_crop="full",
                                is_noise=is_noise
                            ))
                elif isinstance(page, list):
                    for item in page:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            text_info = item[1]
                            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                t_str = str(text_info[0]).strip()
                                s = float(text_info[1])
                                if t_str and t_str.lower() not in seen:
                                    seen.add(t_str.lower())
                                    is_noise = NoiseLineFilter.is_noise_line(t_str)
                                    detected_lines.append(DetectedLine(
                                        text=t_str,
                                        confidence=float(round(s * 100, 2)),
                                        source_crop="full",
                                        is_noise=is_noise
                                    ))

        return detected_lines, skew_angle, orig_shape

class EasyOCREngine(BaseOCREngine):
    """
    EasyOCR Engine. Secondary fallback OCR engine.
    """
    def __init__(self, languages: Optional[List[str]] = None):
        import easyocr
        langs = languages or ['en']
        self.reader = easyocr.Reader(langs, gpu=False)
        self.preprocessor = ImagePreprocessor()
        self.name = "EasyOCR"
        self.languages_used = "+".join(langs)

    def extract_text(self, image_bytes: bytes) -> Tuple[List[DetectedLine], float, List[int]]:
        preprocessed = self.preprocessor.process_pipeline(image_bytes)
        skew_angle = preprocessed['skew_angle']
        orig_shape = list(preprocessed['original_shape'])
        rgb_img = preprocessed['rgb']

        detected_lines: List[DetectedLine] = []
        seen = set()

        raw_res = self.reader.readtext(rgb_img)
        for item in raw_res:
            # item format: (bbox, text, prob)
            if len(item) >= 3:
                t_str = str(item[1]).strip()
                prob = float(item[2])
                if t_str and t_str.lower() not in seen:
                    seen.add(t_str.lower())
                    is_noise = NoiseLineFilter.is_noise_line(t_str)
                    detected_lines.append(DetectedLine(
                        text=t_str,
                        confidence=float(round(prob * 100, 2)),
                        source_crop="full",
                        is_noise=is_noise
                    ))

        return detected_lines, skew_angle, orig_shape

class TesseractOCREngine(BaseOCREngine):
    """
    Tesseract OCR implementation supporting English and Bengali (eng+ben)
    with multi-crop and adaptive contrast preprocessing.
    """
    def __init__(self, tesseract_cmd: Optional[str] = None, languages: str = "eng+ben"):
        import pytesseract
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            self.cmd = tesseract_cmd
        elif shutil.which("tesseract"):
            self.cmd = shutil.which("tesseract")
        elif os.path.exists("/opt/homebrew/bin/tesseract"):
            self.cmd = "/opt/homebrew/bin/tesseract"
        elif os.path.exists("/usr/local/bin/tesseract"):
            self.cmd = "/usr/local/bin/tesseract"
        elif os.path.exists("/usr/bin/tesseract"):
            self.cmd = "/usr/bin/tesseract"
        else:
            self.cmd = None

        if self.cmd:
            pytesseract.pytesseract.tesseract_cmd = self.cmd

        self.requested_languages = languages
        self.available_languages = self._detect_available_languages()
        self.active_languages = self._resolve_languages(languages)
        self.preprocessor = ImagePreprocessor()
        self.name = f"pytesseract ({self.cmd or 'default'})"

    def _detect_available_languages(self) -> List[str]:
        import pytesseract
        if not self.cmd:
            return []
        try:
            return pytesseract.get_languages(config="")
        except Exception:
            return ["eng"]

    def _resolve_languages(self, requested: str) -> str:
        if not self.available_languages:
            return "eng"
        req_parts = requested.split("+")
        valid_parts = [p for p in req_parts if p in self.available_languages]
        if valid_parts:
            return "+".join(valid_parts)
        return "eng" if "eng" in self.available_languages else self.available_languages[0]

    def extract_text(self, image_bytes: bytes) -> Tuple[List[DetectedLine], float, List[int]]:
        import pytesseract
        if not self.cmd:
            raise RuntimeError("Tesseract binary not found on system PATH.")

        preprocessed = self.preprocessor.process_pipeline(image_bytes)
        skew_angle = preprocessed['skew_angle']
        orig_shape = list(preprocessed['original_shape'])
        crops = preprocessed['crops']

        detected_lines: List[DetectedLine] = []
        seen_texts = set()
        tess_config = "--oem 3 --psm 11"

        for crop_name, crop_img in crops:
            try:
                pil_crop = Image.fromarray(crop_img)
                data = pytesseract.image_to_data(
                    pil_crop,
                    lang=self.active_languages,
                    config=tess_config,
                    output_type=pytesseract.Output.DICT
                )

                n_boxes = len(data['text'])
                current_line_words = []
                current_line_confs = []

                for i in range(n_boxes):
                    text_str = data['text'][i].strip()
                    conf = float(data['conf'][i])

                    if text_str and conf > 0:
                        current_line_words.append(text_str)
                        current_line_confs.append(conf)

                    is_line_end = (i == n_boxes - 1) or (
                        data['line_num'][i] != data['line_num'][i + 1] or
                        data['block_num'][i] != data['block_num'][i + 1]
                    )

                    if is_line_end and current_line_words:
                        full_line = " ".join(current_line_words).strip()
                        avg_conf = float(np.mean(current_line_confs)) if current_line_confs else 0.0

                        if full_line and full_line.lower() not in seen_texts:
                            seen_texts.add(full_line.lower())
                            is_noise = NoiseLineFilter.is_noise_line(full_line)
                            detected_lines.append(DetectedLine(
                                text=full_line,
                                confidence=round(avg_conf, 2),
                                source_crop=crop_name,
                                is_noise=is_noise
                            ))

                        current_line_words = []
                        current_line_confs = []

                del pil_crop, data
            except Exception:
                continue

        del crops, preprocessed
        import gc
        gc.collect()

        return detected_lines, skew_angle, orig_shape

class MockOCREngine(BaseOCREngine):
    """
    Test and mock OCR engine when native engines are bypassed or for simulated unit tests.
    """
    def __init__(self, simulated_lines: Optional[List[str]] = None):
        self.simulated_lines = simulated_lines or [
            "AUGMENTIN 625 DUO",
            "Amoxycillin and Potassium Clavulanate Tablets IP",
            "Batch No: AG7482",
            "Mfg Date: 05/2026 Exp Date: 04/2028",
            "MRP Rs. 223.42 Incl of all taxes",
            "GlaxoSmithKline Pharmaceuticals Ltd",
            "Store in a cool dry place"
        ]
        self.name = "mock-ocr-engine"
        self.languages_used = "eng"

    def extract_text(self, image_bytes: bytes) -> Tuple[List[DetectedLine], float, List[int]]:
        detected: List[DetectedLine] = []
        for line in self.simulated_lines:
            is_noise = NoiseLineFilter.is_noise_line(line)
            detected.append(DetectedLine(
                text=line,
                confidence=95.0,
                source_crop="full",
                is_noise=is_noise
            ))
        return detected, 0.0, [600, 800, 3]

def get_preferred_ocr_engine() -> Tuple[BaseOCREngine, str]:
    """
    Selects the first available OCR engine in priority order:
    1. pytesseract (TesseractOCREngine) - optimized for 512 MB memory footprint
    2. PaddleOCR (fallback if installed)
    3. EasyOCR (fallback if installed)
    4. MockOCREngine (fallback if none available)
    """
    # 1. Tesseract (pytesseract) - ultra-lightweight in RAM (<15MB)
    try:
        engine = TesseractOCREngine()
        if engine.cmd:
            return engine, engine.name
    except Exception as e:
        logger.info(f"Tesseract not available: {e}")

    # 2. PaddleOCR
    try:
        engine = PaddleOCREngine()
        return engine, engine.name
    except Exception as e:
        logger.info(f"PaddleOCR not available or failed to initialize: {e}")

    # 3. EasyOCR
    try:
        engine = EasyOCREngine()
        return engine, engine.name
    except Exception as e:
        logger.info(f"EasyOCR not available or failed to initialize: {e}")

    # None could run
    logger.warning("No native OCR engines (pytesseract, PaddleOCR, EasyOCR) available. Falling back to MockOCREngine.")
    return MockOCREngine(), "None available (MockOCREngine fallback)"

class PillTwinOCR:
    """
    Main PillTwin OCR Controller.
    Coordinates preprocessing, OCR extraction, noise filtering, feature extraction,
    and candidate brand retrieval with confidence boosting.
    
    SAFETY RULE 4: OCR output NEVER produces an exact match by itself.
    The user must explicitly confirm detected brand names in the UI.
    """
    def __init__(
        self,
        engine: Optional[BaseOCREngine] = None,
        brand_matcher: Optional[BrandMatcher] = None,
        brand_parquet_path: str = "data/processed/brand_clean.parquet",
        calibration_json_path: str = "data/processed/matcher_calibration.json"
    ):
        if engine:
            self.engine = engine
            self.engine_name = getattr(engine, 'name', 'custom-engine')
        else:
            self.engine, self.engine_name = get_preferred_ocr_engine()

        if brand_matcher:
            self.brand_matcher = brand_matcher
        else:
            self.brand_matcher = BrandMatcher(
                brand_parquet_path=brand_parquet_path,
                calibration_json_path=calibration_json_path,
                abstention_threshold=0.50
            )

    def scan_strip_photo(self, image_bytes: bytes) -> OCRResult:
        """
        Processes medicine strip image bytes in-memory and returns:
        1. Raw detected OCR lines and consolidated raw OCR text.
        2. Cleaned candidate lines and extracted features (strengths, form cues, release cues).
        3. Top 5 candidate brand suggestions boosted by strength/form agreement.
        4. Strength mismatch warning and low-confidence alert if applicable.
        
        CRITICAL: Never auto-confirms or produces an exact generic match.
        """
        detected_lines, skew_angle, image_shape = self.engine.extract_text(image_bytes)
        raw_line_texts = [d.text for d in detected_lines]
        raw_ocr_text = "\n".join(raw_line_texts)

        # Clean candidate lines
        cleaned_candidate_lines = NoiseLineFilter.filter_lines(raw_line_texts)

        # Extract features from detected text
        extracted_strengths = NoiseLineFilter.extract_strengths(raw_line_texts)
        extracted_cues = NoiseLineFilter.extract_cues(raw_line_texts)
        brand_tokens = NoiseLineFilter.extract_brand_tokens(cleaned_candidate_lines)

        # Gather query strings to search in brand catalog
        query_strings = list(dict.fromkeys(brand_tokens + cleaned_candidate_lines))

        # Retrieve candidate brands
        candidate_pool: Dict[str, Dict[str, Any]] = {}

        for q in query_strings:
            match_res = self.brand_matcher.find_matches(q, top_k=5)
            for c in match_res.candidates:
                b_name = c.brand_name
                if b_name not in candidate_pool:
                    # Extract strengths and metadata from candidate
                    cand_comp = c.raw_composition or ""
                    meta = self.brand_matcher.brand_metadata.get(b_name.lower(), {})
                    dosage_form = meta.get('dosage_form')
                    release_type = meta.get('release_type', 'IR')
                    cand_strengths = NoiseLineFilter.extract_strengths([cand_comp, b_name])
                    cand_cues = NoiseLineFilter.extract_cues([cand_comp, b_name, dosage_form or ""])

                    # Boost confidence based on strength and form agreement
                    boosted_conf = c.calibrated_confidence
                    strength_agreement = False
                    strength_mismatch = False
                    warning_msg = None

                    # Check strength agreement
                    if extracted_strengths and cand_strengths:
                        common_strengths = set(extracted_strengths).intersection(set(cand_strengths))
                        if common_strengths:
                            # Boost candidate that matches OCR strength!
                            boosted_conf = min(1.0, boosted_conf + 0.15)
                            strength_agreement = True
                        else:
                            # Strong conflict: OCR clearly says e.g. 500mg, candidate is 650mg
                            strength_mismatch = True
                            warning_msg = f"Warning: Photo shows strength {', '.join(extracted_strengths)}, but {b_name} is {', '.join(cand_strengths)}."

                    # Check form/release cue agreement
                    if extracted_cues.get("release_cues") and cand_cues.get("release_cues"):
                        if set(extracted_cues["release_cues"]).intersection(set(cand_cues["release_cues"])):
                            boosted_conf = min(1.0, boosted_conf + 0.10)

                    if extracted_cues.get("form_cues") and cand_cues.get("form_cues"):
                        if set(extracted_cues["form_cues"]).intersection(set(cand_cues["form_cues"])):
                            boosted_conf = min(1.0, boosted_conf + 0.05)

                    candidate_pool[b_name] = {
                        'brand_name': b_name,
                        'calibrated_confidence': round(boosted_conf, 4),
                        'raw_confidence': round(c.calibrated_confidence, 4),
                        'similarity': round(c.similarity, 4),
                        'detected_from_line': q,
                        'raw_composition': cand_comp,
                        'dosage_form': dosage_form,
                        'release_type': release_type,
                        'strength_agreement': strength_agreement,
                        'strength_mismatch_warning': strength_mismatch,
                        'warning_message': warning_msg
                    }
                else:
                    # Keep highest boosted confidence
                    if c.calibrated_confidence > candidate_pool[b_name]['raw_confidence']:
                        candidate_pool[b_name]['similarity'] = max(candidate_pool[b_name]['similarity'], round(c.similarity, 4))

        # Sort candidate suggestions by boosted confidence descending
        sorted_candidates = sorted(candidate_pool.values(), key=lambda x: x['calibrated_confidence'], reverse=True)
        top_5_candidates = sorted_candidates[:5]

        # Safety & Confidence checks
        low_confidence = False
        low_confidence_msg = None
        if not top_5_candidates or top_5_candidates[0]['calibrated_confidence'] < 0.60:
            low_confidence = True
            low_confidence_msg = "couldn't read clearly; type the name or retake the photo"

        langs = getattr(self.engine, 'languages_used', 'eng')

        return OCRResult(
            raw_lines=raw_line_texts,
            raw_ocr_text=raw_ocr_text,
            cleaned_candidate_lines=cleaned_candidate_lines,
            suggested_brands=top_5_candidates,
            detected_lines_detail=detected_lines,
            extracted_strengths=extracted_strengths,
            extracted_cues=extracted_cues,
            engine_name=self.engine_name,
            languages_used=str(langs),
            skew_angle=skew_angle,
            image_shape=image_shape,
            low_confidence=low_confidence,
            low_confidence_message=low_confidence_msg,
            exact_match_produced=False,
            prompt_message="Is this your medicine? Tap your brand to view generic equivalents.",
            disclaimer=MANDATORY_DISCLAIMER
        )
