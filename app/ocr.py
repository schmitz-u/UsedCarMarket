from __future__ import annotations

import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

_tesseract_available: Optional[bool] = None


def _check_tesseract() -> bool:
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _tesseract_available = True
    except Exception:
        _tesseract_available = False
    return _tesseract_available


def run_ocr(image: Image.Image, lang: str = "deu+eng") -> str:
    """
    Run OCR on a PIL Image and return extracted text.

    Falls back to empty string with a warning when Tesseract is not available.
    """
    if not _check_tesseract():
        logger.warning("Tesseract is not available; returning empty OCR text")
        return ""
    try:
        import pytesseract
        text = pytesseract.image_to_string(image, lang=lang)
        return text
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return ""


def run_ocr_from_path(path: str, lang: str = "deu+eng") -> str:
    """Run OCR on an image file specified by path."""
    try:
        img = Image.open(path).convert("RGB")
    except Exception as exc:
        logger.error("Cannot open image %s: %s", path, exc)
        return ""
    return run_ocr(img, lang=lang)


def run_ocr_from_bytes(data: bytes, lang: str = "deu+eng") -> str:
    """Run OCR on raw image bytes."""
    import io
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        logger.error("Cannot decode image bytes: %s", exc)
        return ""
    return run_ocr(img, lang=lang)
