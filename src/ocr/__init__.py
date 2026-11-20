"""
PillTwin OCR Module.
Provides privacy-preserving in-memory optical character recognition for medicine strips and packaging.
Features OpenCV pre-processing (contrast enhancement, deskew, adaptive thresholding, multi-crop)
and noise line filtering behind a swappable OCR engine interface.
"""

from src.ocr.preprocessor import ImagePreprocessor
from src.ocr.filters import NoiseLineFilter
from src.ocr.engine import BaseOCREngine, TesseractOCREngine, PillTwinOCR, OCRResult, DetectedLine

__all__ = [
    'ImagePreprocessor',
    'NoiseLineFilter',
    'BaseOCREngine',
    'TesseractOCREngine',
    'PillTwinOCR',
    'OCRResult',
    'DetectedLine'
]
