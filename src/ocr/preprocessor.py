import io
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageOps
import cv2

class ImagePreprocessor:
    """
    OpenCV and PIL in-memory image preprocessor for medicine strip/box OCR.
    Enforces Non-Negotiable Rule 6: Processed strictly in memory, zero disk writes,
    EXIF metadata stripped immediately on ingestion.
    """

    @staticmethod
    def strip_exif_and_decode(image_bytes: bytes, max_long_side: int = 1600) -> np.ndarray:
        """
        Decodes raw image bytes in memory, strips all EXIF metadata,
        caps image dimension to max_long_side (1600 px) on the long side,
        corrects orientation if needed, and returns an RGB numpy array.
        """
        if not image_bytes:
            raise ValueError("Input image bytes cannot be empty.")

        with io.BytesIO(image_bytes) as bio:
            with Image.open(bio) as pil_img:
                # Transpose according to EXIF orientation tag then strip metadata
                try:
                    pil_img = ImageOps.exif_transpose(pil_img)
                except Exception:
                    pass

                # Cap image to max_long_side (1600 px) on the long side
                w, h = pil_img.size
                if max(w, h) > max_long_side:
                    scale = max_long_side / float(max(w, h))
                    new_w = max(1, int(round(w * scale)))
                    new_h = max(1, int(round(h * scale)))
                    pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Convert to RGB (drops alpha channel and strips all metadata dictionaries)
                rgb_img = pil_img.convert("RGB")
                img_array = np.array(rgb_img)

        return img_array

    @staticmethod
    def upscale_if_small(image: np.ndarray, min_dim: int = 600) -> np.ndarray:
        """
        Upscales small cropped/thumbnail images using bicubic interpolation
        to ensure text features have sufficient resolution for OCR character recognition.
        """
        h, w = image.shape[:2]
        if max(h, w) < min_dim or min(h, w) < 250:
            scale = max(min_dim / max(h, w), 250 / max(min(h, w), 1), 2.0)
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return image

    @staticmethod
    def enhance_contrast(image: np.ndarray, clip_limit: float = 2.5, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """
        Enhances image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        applied to the L (Lightness) channel in LAB color space.
        """
        if len(image.shape) == 2:
            # Grayscale
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            return clahe.apply(image)

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l)

        limg = cv2.merge((cl, a, b))
        enhanced_rgb = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        return enhanced_rgb

    @staticmethod
    def deskew(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detects text orientation/skew angle and rotates the image to upright alignment.
        Returns the deskewed image and the detected angle in degrees.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()

        # Invert colors so text is foreground (white) on dark background
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find all foreground pixels
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return image, 0.0

        # Compute minimum area bounding box
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # Determine true text skew angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # If angle is negligible (< 0.5 degrees) or extreme (> 45 degrees), skip rotation
        if abs(angle) < 0.5 or abs(angle) > 45.0:
            return image, 0.0

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            m,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated, float(round(angle, 2))

    @staticmethod
    def binarize_adaptive(gray: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Generates multiple complementary binarized representations for robust text extraction
        across reflective foil strips, glossy boxes, and uneven lighting.
        """
        # 1. Otsu thresholding with slight Gaussian blur
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 2. Adaptive Gaussian thresholding (robust against local shadows and reflections)
        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=25,
            C=11
        )

        # 3. Morphological opening to clean small speckle noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned_adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, kernel)

        return {
            'otsu': otsu,
            'adaptive': adaptive,
            'cleaned_adaptive': cleaned_adaptive
        }

    @staticmethod
    def generate_crops(image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Generates targeted crops of the image (full, central, top-half, bottom-half)
        to isolate brand and strength lines on crowded medicine packaging.
        """
        h, w = image.shape[:2]
        crops = [("full", image)]

        if h >= 100 and w >= 100:
            # Central 80%
            y1, y2 = int(h * 0.1), int(h * 0.9)
            x1, x2 = int(w * 0.1), int(w * 0.9)
            crops.append(("center", image[y1:y2, x1:x2]))

            # Top half (often contains primary brand trade name)
            crops.append(("top_half", image[0:int(h * 0.6), :]))

            # Bottom half (often contains generic formulation, strength, and license)
            crops.append(("bottom_half", image[int(h * 0.4):h, :]))

        return crops

    def process_pipeline(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Executes the full in-memory preprocessing pipeline:
        1. Decode and strip EXIF
        2. Contrast enhancement via CLAHE
        3. Skew estimation and deskew
        4. Grayscale conversion and adaptive thresholding
        5. Targeted crop extraction
        """
        rgb_img = self.strip_exif_and_decode(image_bytes)
        upscaled_rgb = self.upscale_if_small(rgb_img)
        enhanced_rgb = self.enhance_contrast(upscaled_rgb)
        deskewed_rgb, skew_angle = self.deskew(enhanced_rgb)

        gray = cv2.cvtColor(deskewed_rgb, cv2.COLOR_RGB2GRAY)
        binarized = self.binarize_adaptive(gray)
        crops = self.generate_crops(deskewed_rgb)

        return {
            'original_shape': rgb_img.shape,
            'skew_angle': skew_angle,
            'rgb': deskewed_rgb,
            'gray': gray,
            'binarized': binarized,
            'crops': crops
        }
