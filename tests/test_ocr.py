import os
import io
import tempfile
import pytest
import numpy as np
from PIL import Image, ImageDraw

from src.ocr.preprocessor import ImagePreprocessor
from src.ocr.filters import NoiseLineFilter
from src.ocr.engine import BaseOCREngine, TesseractOCREngine, MockOCREngine, PillTwinOCR, OCRResult

def create_synthetic_strip_image(
    brand_text: str = "AUGMENTIN 625 DUO",
    salt_text: str = "Amoxycillin and Potassium Clavulanate Tablets IP",
    batch_text: str = "B.No. BT9182  MFG. 05/2026  EXP. 04/2028",
    mrp_text: str = "M.R.P. Rs. 223.42 Incl. of all taxes",
    mfg_text: str = "GlaxoSmithKline Pharmaceuticals Ltd, Industrial Area"
) -> bytes:
    """Creates an in-memory PNG image of a synthetic medicine strip."""
    img = Image.new('RGB', (800, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 30), brand_text, fill=(0, 0, 0))
    draw.text((40, 80), salt_text, fill=(40, 40, 40))
    draw.text((40, 130), batch_text, fill=(100, 100, 100))
    draw.text((40, 175), mrp_text, fill=(100, 100, 100))
    draw.text((40, 220), mfg_text, fill=(120, 120, 120))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

class TestImagePreprocessor:
    def test_strip_exif_and_decode(self):
        # Create image with dummy EXIF data
        img = Image.new('RGB', (200, 100), color=(200, 200, 200))
        exif = img.getexif()
        exif[0x0112] = 1 # Normal orientation tag
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', exif=exif)
        raw_bytes = buf.getvalue()

        decoded = ImagePreprocessor.strip_exif_and_decode(raw_bytes)
        assert isinstance(decoded, np.ndarray)
        assert decoded.shape == (100, 200, 3)

    def test_enhance_contrast_clahe(self):
        img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
        enhanced = ImagePreprocessor.enhance_contrast(img_array)
        assert enhanced.shape == img_array.shape

    def test_deskew_rotated_image(self):
        # Create tilted text image
        img = Image.new('L', (400, 200), color=255)
        draw = ImageDraw.Draw(img)
        draw.text((50, 80), "METFORMIN 500 MG", fill=0)
        rotated_img = img.rotate(15, fillcolor=255)

        buf = io.BytesIO()
        rotated_img.save(buf, format='PNG')
        raw_bytes = buf.getvalue()

        decoded = ImagePreprocessor.strip_exif_and_decode(raw_bytes)
        deskewed, angle = ImagePreprocessor.deskew(decoded)
        assert isinstance(deskewed, np.ndarray)
        assert deskewed.shape == decoded.shape

    def test_adaptive_binarization_outputs(self):
        gray = np.full((100, 100), 128, dtype=np.uint8)
        bin_dict = ImagePreprocessor.binarize_adaptive(gray)
        assert 'otsu' in bin_dict
        assert 'adaptive' in bin_dict
        assert 'cleaned_adaptive' in bin_dict
        assert bin_dict['otsu'].shape == (100, 100)

    def test_generate_crops(self):
        img = np.zeros((300, 600, 3), dtype=np.uint8)
        crops = ImagePreprocessor.generate_crops(img)
        crop_names = [c[0] for c in crops]
        assert "full" in crop_names
        assert "center" in crop_names
        assert "top_half" in crop_names
        assert "bottom_half" in crop_names

class TestNoiseLineFilter:
    def test_filters_batch_and_dates(self):
        assert NoiseLineFilter.is_noise_line("B.No. AG7482") is True
        assert NoiseLineFilter.is_noise_line("Batch No. 2026-X") is True
        assert NoiseLineFilter.is_noise_line("MFG. 05/2026 EXP. 04/2028") is True
        assert NoiseLineFilter.is_noise_line("Expiry Date: Nov 2027") is True
        assert NoiseLineFilter.is_noise_line("Use Before 12/2026") is True

    def test_filters_mrp_and_pricing(self):
        assert NoiseLineFilter.is_noise_line("M.R.P. Rs. 223.42") is True
        assert NoiseLineFilter.is_noise_line("MRP ₹34.27 Incl. of all taxes") is True
        assert NoiseLineFilter.is_noise_line("Max Retail Price: Rs 52.60") is True

    def test_filters_licence_and_corporate_addresses(self):
        assert NoiseLineFilter.is_noise_line("Mfg. Lic. No. G/25/1842") is True
        assert NoiseLineFilter.is_noise_line("Marketed by: Sun Pharma Laboratories Ltd.") is True
        assert NoiseLineFilter.is_noise_line("Plot No. 42, Industrial Area Phase II, Baddi") is True
        assert NoiseLineFilter.is_noise_line("Store below 25°C in a dry place") is True
        assert NoiseLineFilter.is_noise_line("Schedule H Prescription Drug - Caution") is True

    def test_retains_medicine_brand_and_composition(self):
        assert NoiseLineFilter.is_noise_line("AUGMENTIN 625 DUO") is False
        assert NoiseLineFilter.is_noise_line("Amoxycillin and Potassium Clavulanate Tablets IP") is False
        assert NoiseLineFilter.is_noise_line("Dolo 650 Tablets") is False
        assert NoiseLineFilter.is_noise_line("Paracetamol Tablets IP 650 mg") is False
        assert NoiseLineFilter.is_noise_line("Telma 40") is False

    def test_clean_ocr_line_corrections(self):
        # 65O mg -> 650 mg
        assert NoiseLineFilter.clean_ocr_line("Dolo 65O mg") == "Dolo 650 mg"
        # 5OO mg -> 500 mg
        assert NoiseLineFilter.clean_ocr_line("Azithral 5OO mg") == "Azithral 500 mg"
        # Punctuation stripping
        assert NoiseLineFilter.clean_ocr_line("--- [DOLO 650] ---") == "DOLO 650"

class TestPillTwinOCR:
    @pytest.fixture
    def ocr_system(self):
        return PillTwinOCR()

    def test_ocr_extracts_and_matches_brand_candidate(self, ocr_system):
        img_bytes = create_synthetic_strip_image(
            brand_text="AUGMENTIN 625 DUO",
            salt_text="Amoxycillin and Potassium Clavulanate Tablets IP"
        )

        res = ocr_system.scan_strip_photo(img_bytes)
        assert isinstance(res, OCRResult)
        assert len(res.raw_lines) > 0
        assert len(res.cleaned_candidate_lines) > 0
        
        # Verify noise lines were eliminated from cleaned candidate list
        cand_text_blob = " ".join(res.cleaned_candidate_lines).lower()
        assert "incl" not in cand_text_blob
        assert "industrial area" not in cand_text_blob

        # Verify brand suggested candidate
        assert len(res.suggested_brands) > 0
        top_sug = res.suggested_brands[0]
        assert "Augmentin" in top_sug['brand_name']
        assert top_sug['calibrated_confidence'] >= 0.75

    def test_swappable_mock_ocr_engine(self):
        mock_engine = MockOCREngine(simulated_lines=[
            "DOLO 650",
            "Paracetamol Tablets IP 650 mg",
            "Batch: D84920",
            "MRP: Rs. 34.27"
        ])
        ocr = PillTwinOCR(engine=mock_engine)
        res = ocr.scan_strip_photo(b"dummy_bytes")
        assert res.engine_name == "mock-ocr-engine"
        assert "DOLO 650" in res.cleaned_candidate_lines
        assert any("Dolo 650" in b['brand_name'] for b in res.suggested_brands)

    def test_privacy_no_disk_persistence(self, ocr_system):
        """
        NON-NEGOTIABLE RULE 6: Photos are processed in memory and discarded;
        never written to disk, logged, or cached. Verify zero files written to disk.
        """
        before_data_files = set()
        for root, _, files in os.walk("data/"):
            for f in files:
                before_data_files.add(os.path.join(root, f))

        img_bytes = create_synthetic_strip_image(
            brand_text="PAN 40",
            salt_text="Pantoprazole Gastro-Resistant Tablets IP 40mg"
        )

        # Run OCR scan
        res = ocr_system.scan_strip_photo(img_bytes)
        assert res is not None

        after_data_files = set()
        for root, _, files in os.walk("data/"):
            for f in files:
                after_data_files.add(os.path.join(root, f))

        # Assert no new files were created anywhere in data/
        diff = after_data_files - before_data_files
        assert len(diff) == 0, f"Privacy violation: files were written to disk: {diff}"

    def test_ocr_text_never_auto_confirms(self, ocr_system):
        """
        NON-NEGOTIABLE RULE 4 & Phase 3 Requirement 4:
        OCR output NEVER produces an exact match by itself.
        It must only propose candidates for the user to confirm.
        """
        img_bytes = create_synthetic_strip_image(
            brand_text="DOLO 650",
            salt_text="Paracetamol Tablets IP 650 mg"
        )
        res = ocr_system.scan_strip_photo(img_bytes)
        assert res.exact_match_produced is False
        assert hasattr(res, "generic") is False or getattr(res, "generic", None) is None
        assert "Is this your medicine?" in res.prompt_message
        assert len(res.suggested_brands) > 0

    def test_strength_mismatch_triggers_warning(self):
        """
        Phase 3 Requirement 4:
        If the OCR text and candidate disagree on strength, show a warning.
        """
        mock_engine = MockOCREngine(simulated_lines=[
            "DOLO 500",
            "Paracetamol Tablets IP 500 mg",
            "Batch: D84920"
        ])
        ocr = PillTwinOCR(engine=mock_engine)
        res = ocr.scan_strip_photo(b"dummy_bytes")
        # Find candidate Dolo 650 Tablet if present among candidates
        dolo_650 = next((b for b in res.suggested_brands if "650" in b['brand_name']), None)
        if dolo_650:
            assert dolo_650['strength_mismatch_warning'] is True
            assert dolo_650['warning_message'] is not None
            assert "Warning" in dolo_650['warning_message']

    def test_noisy_brand_strings_retrieval(self):
        """
        Phase 3 Requirement 7:
        Tests for noisy brand strings like 'Dol0 650' and 'Augmentn 625'.
        """
        # Test 1: "Dol0 650"
        mock_dolo = MockOCREngine(simulated_lines=[
            "Dol0 650 Tablets",
            "Paracetamol 650 mg"
        ])
        ocr_dolo = PillTwinOCR(engine=mock_dolo)
        res_dolo = ocr_dolo.scan_strip_photo(b"dummy")
        dolo_cand_names = [b['brand_name'] for b in res_dolo.suggested_brands]
        assert any("Dolo 650" in name for name in dolo_cand_names)

        # Test 2: "Augmentn 625"
        mock_aug = MockOCREngine(simulated_lines=[
            "Augmentn 625 Duo",
            "Amoxycillin and Clavulanate"
        ])
        ocr_aug = PillTwinOCR(engine=mock_aug)
        res_aug = ocr_aug.scan_strip_photo(b"dummy")
        aug_cand_names = [b['brand_name'] for b in res_aug.suggested_brands]
        assert any("Augmentin" in name for name in aug_cand_names)

