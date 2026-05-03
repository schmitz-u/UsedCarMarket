from __future__ import annotations

import hashlib
import re
from typing import Optional


def normalize_price(raw: str) -> Optional[float]:
    """Convert German price string like '39.990 €' or '€ 12.000' to float."""
    if not raw:
        return None
    cleaned = re.sub(r"[€$\s]", "", raw)
    cleaned = cleaned.replace(".", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_mileage(raw: str) -> Optional[int]:
    """Convert German mileage string like '19.600 km' or '0\xa0km' to int."""
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    try:
        return int(digits)
    except ValueError:
        return None


def normalize_power_kw(raw: str) -> Optional[float]:
    """Extract kW value from strings like '93 kW (126 PS)' or '87 kW (118 PS)'."""
    if not raw:
        return None
    m = re.search(r"([\d,\.]+)\s*kW", raw, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def normalize_displacement(raw: str) -> Optional[int]:
    """Extract displacement in cc from strings like '1.800 cm³', '1833 cm3', or '1830 ccm'."""
    if not raw:
        return None
    m = re.search(r"([\d\s\.\,]+)\s*(?:cm[²³3]|ccm|cc)\b", raw, re.IGNORECASE)
    if m:
        digits = re.sub(r"[^\d]", "", m.group(1))
        try:
            val = int(digits)
            if 50 <= val <= 10000:
                return val
        except ValueError:
            pass
    digits = re.sub(r"[^\d]", "", raw.split()[0] if raw.strip() else "")
    try:
        val = int(digits)
        if 50 <= val <= 10000:
            return val
    except ValueError:
        pass
    return None


def normalize_first_registration(raw: str) -> tuple[Optional[str], Optional[int]]:
    """
    Parse first registration string.

    Returns (first_registration_str, year_int).
    Accepts '03/2026', '04/2016', etc.
    """
    if not raw:
        return None, None
    m = re.search(r"(\d{1,2})[/\-.](\d{4})", raw)
    if m:
        month, year = m.group(1), m.group(2)
        return f"{int(month):02d}/{year}", int(year)
    m = re.search(r"(\d{4})", raw)
    if m:
        return m.group(1), int(m.group(1))
    return None, None


def normalize_previous_owners(raw: str) -> Optional[int]:
    """Extract integer number of previous owners."""
    if not raw:
        return None
    m = re.search(r"\d+", raw)
    try:
        return int(m.group()) if m else None
    except ValueError:
        return None


def generate_fingerprint(brand: Optional[str], model: Optional[str], year: Optional[int],
                          mileage_km: Optional[int], price_amount: Optional[float] = None) -> str:
    """
    Generate a deterministic listing fingerprint for dedup when URL is absent.
    Uses brand + model + year + mileage (price excluded to remain stable across
    price changes for the same physical listing).
    """
    parts = [
        (brand or "").lower().strip(),
        (model or "").lower().strip(),
        str(year or ""),
        str(mileage_km or ""),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def detect_portal(text: str) -> Optional[str]:
    """Detect which portal a screenshot came from based on OCR text content."""
    if re.search(r"mobile\.de", text, re.IGNORECASE):
        return "mobile.de"
    if re.search(r"autoscout24", text, re.IGNORECASE):
        return "autoscout24"
    return None
