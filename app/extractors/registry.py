from __future__ import annotations

import re

from app.models import ExtractionResult, FieldExtraction
from app.normalizers import detect_portal
from app.extractors import mobile_de, autoscout24 as as24

EXTRACTORS = {
    "mobile.de": mobile_de.extract,
    "autoscout24": as24.extract,
}


def detect_and_extract(ocr_text: str) -> ExtractionResult:
    """
    Detect the portal from OCR text and run the matching extractor.
    Falls back to a generic scan when portal cannot be determined.
    """
    portal = detect_portal(ocr_text)
    if portal and portal in EXTRACTORS:
        return EXTRACTORS[portal](ocr_text)

    # Heuristic: try both and return the one with higher overall confidence
    results = [fn(ocr_text) for fn in EXTRACTORS.values()]
    results.sort(key=lambda r: r.overall_confidence(), reverse=True)
    best = results[0]
    if best.overall_confidence() == 0.0:
        best.source_marketplace = None
    return best
