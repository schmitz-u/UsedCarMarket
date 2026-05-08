from __future__ import annotations

import hashlib
import re
from typing import Optional


_BRAND_ALIASES = {
    "honda": "Honda",
    "bmw": "BMW",
    "yamaha": "Yamaha",
    "kawasaki": "Kawasaki",
    "suzuki": "Suzuki",
    "ducati": "Ducati",
    "ktm": "KTM",
}

_FAMILY_PATTERNS = [
    re.compile(r"\bgold[-\s]*wing\b", re.I),
    re.compile(r"\bgoldwing\b", re.I),
]

_VARIANT_PATTERNS = [
    (re.compile(r"\bgl[-\s]*1000\b", re.I), "GL 1000"),
    (re.compile(r"\b1000\b", re.I), "GL 1000"),
    (re.compile(r"\bgl[-\s]*1100\b", re.I), "GL 1100"),
    (re.compile(r"\b1100\b", re.I), "GL 1100"),
    (re.compile(r"\bgl[-\s]*1200\b", re.I), "GL 1200"),
    (re.compile(r"\b1200\b", re.I), "GL 1200"),
    (re.compile(r"\bgl[-\s]*1500\b", re.I), "GL 1500"),
    (re.compile(r"\b1500\b", re.I), "GL 1500"),
    (re.compile(r"\bgl\s*1800\b", re.I), "GL 1800"),
    (re.compile(r"\b1800\b", re.I), "GL 1800"),
]

_TRIM_PATTERNS = [
    (re.compile(r"\bf[6bgöóo]b\b", re.I), "F6B"),
    (re.compile(r"\bbagger\b", re.I), "Bagger"),
    (re.compile(r"\btourer\b", re.I), "Tourer"),
    (re.compile(r"\btouring\b", re.I), "Tour"),
    (re.compile(r"\btour\b", re.I), "Tour"),
]

_GEARBOX_PATTERNS = [
    (re.compile(r"\bdct\b", re.I), "DCT"),
    (re.compile(r"\bautomatik\b", re.I), "Automatik"),
    (re.compile(r"\bschalt(getriebe)?\b", re.I), "Schaltgetriebe"),
]

_MARKETING_TAG_PATTERNS = [
    (re.compile(r"\btop\b", re.I), "TOP"),
    (re.compile(r"\bwinterpreis\b", re.I), "WINTERPREIS"),
    (re.compile(r"\bgebraucht\b", re.I), "GEBRAUCHT"),
]

_OWNERSHIP_PATTERNS = [
    re.compile(r"\b1\.?\s*hand\b", re.I),
    re.compile(r"\berste\s+hand\b", re.I),
]

_SELLER_PATTERNS = [
    (re.compile(r"\b(h[aä]ndler|haendler|dealer|gewerb\w*)\b", re.I), "Händler"),
    (re.compile(r"\b(privat|privatanbieter|private)\b", re.I), "Privat"),
]

_SERIES_CODE_PATTERN = re.compile(r"\bsc[-\s]*\d{2,3}[a-z]?\b", re.I)


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


def generate_fingerprint(
    brand: Optional[str],
    model: Optional[str],
    year: Optional[int],
    mileage_km: Optional[int],
    price_amount: Optional[float] = None,
) -> str:
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


class HarmonizationConflict(ValueError):
    """Raised when extracted year and model attributes are mutually implausible."""


# ---------------------------------------------------------------------------
# Year validity windows derived from Honda Gold Wing family history.
# Each rule is (description, condition_fn) evaluated after harmonization.
# ---------------------------------------------------------------------------

# Maps each Gold Wing variant to its known production year range.
_VARIANT_YEAR_RANGES: dict[str, tuple[int, int]] = {
    "GL 1000": (1975, 1979),
    "GL 1100": (1980, 1983),
    "GL 1200": (1984, 1987),
    "GL 1500": (1988, 2000),
    "GL 1800": (2001, 2026),
}

# Trim/feature windows: (first_year, last_year).
# None means open-ended (still in production).
_TRIM_YEAR_RANGES: dict[str, tuple[int, Optional[int]]] = {
    "F6B": (2013, 2016),
    "Tour": (1980, None),  # Interstate/Aspencade from GL1100 onward
    "Bagger": (2013, None),  # F6B era → modern Bagger
}

# DCT was introduced with the 2018 platform.
_DCT_MIN_YEAR = 2018
_REGISTRATION_LAG_YEARS = 2


def validate_harmonized_listing(
    harmonized: dict[str, Optional[str]],
    year: Optional[int],
) -> None:
    """
    Raise HarmonizationConflict when the year contradicts the
    normalised variant, trim, or drivetrain attributes.
    """
    if year is None:
        return  # Cannot validate without a year; skip.

    variant = harmonized.get("model_variant_normalized")
    trim_raw = harmonized.get("trim_normalized") or ""
    trims = [t.strip() for t in trim_raw.split("/") if t.strip()]
    gearbox = harmonized.get("drivetrain_or_gearbox_normalized") or ""

    # 1. Variant vs. year
    if variant and variant in _VARIANT_YEAR_RANGES:
        lo, hi = _VARIANT_YEAR_RANGES[variant]
        if not (lo <= year <= hi + _REGISTRATION_LAG_YEARS):
            raise HarmonizationConflict(
                f"Year {year} is outside the known production range "
                f"{lo}–{hi} for {variant}."
            )

    # 2. Trim vs. year
    for trim in trims:
        if trim in _TRIM_YEAR_RANGES:
            lo, hi = _TRIM_YEAR_RANGES[trim]
            hi_display = hi if hi is not None else "present"
            if year < lo or (
                hi is not None and year > hi + _REGISTRATION_LAG_YEARS
            ):
                raise HarmonizationConflict(
                    f"Year {year} is outside the known production range "
                    f"{lo}–{hi_display} for trim '{trim}'."
                )

    # 3. DCT vs. year
    if gearbox == "DCT" and year < _DCT_MIN_YEAR:
        raise HarmonizationConflict(
            f"DCT gearbox was introduced in {_DCT_MIN_YEAR}; year {year} predates it."
        )


def detect_portal(text: str) -> Optional[str]:
    """Detect which portal a screenshot came from based on OCR text content."""
    if re.search(r"mobile\.de", text, re.IGNORECASE):
        return "mobile.de"
    if re.search(r"autoscout24", text, re.IGNORECASE):
        return "autoscout24"
    return None


def harmonize_listing_title(
    brand: Optional[str],
    model: Optional[str],
    transmission: Optional[str] = None,
    condition: Optional[str] = None,
    year: Optional[int] = None,
    source_url: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Normalize noisy title fragments into canonical motorcycle model attributes."""
    raw_brand = (brand or "").strip()
    raw_model = (model or "").strip()
    raw_transmission = (transmission or "").strip()
    raw_condition = (condition or "").strip()
    raw_url = (source_url or "").strip()

    brand_norm = _normalize_brand(raw_brand)
    text_blob = " ".join(
        x for x in [raw_model, raw_transmission, raw_condition, raw_url] if x
    ).strip()

    family = _detect_family(text_blob, brand_norm)
    variant = _detect_variant(text_blob, family, year)
    trims = _detect_trims(text_blob, family, variant, year)
    gearbox = _detect_gearbox(text_blob)
    series_code = _detect_series_code(text_blob)
    marketing_tags = _detect_marketing_tags(text_blob)
    ownership_hint = _detect_ownership_hint(text_blob)
    seller_norm = normalize_seller_type(raw_condition)

    title_harmonized = _compose_harmonized_title(
        brand_norm, family, variant, trims, gearbox, series_code
    )

    return {
        "brand_normalized": brand_norm,
        "model_family_normalized": family,
        "model_variant_normalized": variant,
        "series_identifier": series_code,
        "trim_normalized": " / ".join(trims) if trims else None,
        "drivetrain_or_gearbox_normalized": gearbox,
        "marketing_tags_json": ",".join(marketing_tags) if marketing_tags else None,
        "ownership_hint": ownership_hint,
        "seller_normalized": seller_norm,
        "title_raw": raw_model or None,
        "title_harmonized": title_harmonized,
    }


def normalize_seller_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    for pat, label in _SELLER_PATTERNS:
        if pat.search(raw):
            return label
    return None


def _normalize_brand(raw_brand: str) -> Optional[str]:
    if not raw_brand:
        return None
    key = raw_brand.lower().strip()
    return _BRAND_ALIASES.get(key, raw_brand.strip())


def _detect_family(text_blob: str, brand_norm: Optional[str]) -> Optional[str]:
    for pat in _FAMILY_PATTERNS:
        if pat.search(text_blob):
            return "Gold Wing"
    if brand_norm == "Honda" and re.search(
        r"\b(f6b|gl\s*(1000|1100|1200|1500|1800)|1800)\b", text_blob, re.I
    ):
        return "Gold Wing"
    return None


def _detect_variant(
    text_blob: str, family: Optional[str], year: Optional[int]
) -> Optional[str]:
    if not family:
        return None
    m = re.search(r"\bgl[-\s]*(1000|1100|1200|1500|1800)\b", text_blob, re.I)
    if m:
        return f"GL {m.group(1)}"
    for pat, label in _VARIANT_PATTERNS:
        if pat.search(text_blob):
            return label

    # Year-informed fallback from Gold Wing family history.
    if year is not None:
        if 1975 <= year <= 1979:
            return "GL 1000"
        if 1980 <= year <= 1983:
            return "GL 1100"
        if 1984 <= year <= 1987:
            return "GL 1200"
        if 1988 <= year <= 2000:
            return "GL 1500"
        if year >= 2001:
            return "GL 1800"
    return None


def _detect_trims(
    text_blob: str,
    family: Optional[str],
    variant: Optional[str],
    year: Optional[int],
) -> list[str]:
    trims: list[str] = []
    for pat, label in _TRIM_PATTERNS:
        if pat.search(text_blob):
            normalized = "Tour" if label == "Tourer" else label
            trims.append(normalized)

    # F6B is a bagger-style Gold Wing derivative.
    if "F6B" in trims and "Bagger" not in trims:
        trims.append("Bagger")

    # Year-guided enrichment: bagger naming changed after 2018 platform refresh.
    if (
        year is not None
        and "Bagger" in trims
        and "F6B" not in trims
        and 2013 <= year <= 2016
    ):
        trims.insert(0, "F6B")

    # Default Gold Wing type classification when no explicit trim is found.
    if not trims and family == "Gold Wing":
        if variant in {"GL 1100", "GL 1200", "GL 1500", "GL 1800"}:
            trims.append("Tour")
        elif variant is None and year is not None and year >= 1980:
            trims.append("Tour")

    # De-duplicate while preserving order.
    deduped: list[str] = []
    for t in trims:
        if t not in deduped:
            deduped.append(t)
    return deduped


def _detect_gearbox(text_blob: str) -> Optional[str]:
    for pat, label in _GEARBOX_PATTERNS:
        if pat.search(text_blob):
            return label
    return None


def _detect_marketing_tags(text_blob: str) -> list[str]:
    tags: list[str] = []
    for pat, label in _MARKETING_TAG_PATTERNS:
        if pat.search(text_blob):
            tags.append(label)
    return tags


def _detect_ownership_hint(text_blob: str) -> Optional[str]:
    for pat in _OWNERSHIP_PATTERNS:
        if pat.search(text_blob):
            return "1. Hand"
    return None


def _detect_series_code(text_blob: str) -> Optional[str]:
    m = _SERIES_CODE_PATTERN.search(text_blob)
    if not m:
        return None
    return re.sub(r"[-\s]+", "", m.group(0)).upper()


def infer_engine_displacement_cc(
    variant: Optional[str], year: Optional[int]
) -> Optional[int]:
    """Infer Gold Wing engine displacement when OCR did not capture Hubraum/cc."""
    if variant == "GL 1000":
        return 999
    if variant == "GL 1100":
        return 1085
    if variant == "GL 1200":
        return 1182
    if variant == "GL 1500":
        return 1520
    if variant == "GL 1800":
        if year is not None and year >= 2018:
            return 1833
        return 1832
    return None


def _compose_harmonized_title(
    brand_norm: Optional[str],
    family: Optional[str],
    variant: Optional[str],
    trims: list[str],
    gearbox: Optional[str],
    series_code: Optional[str],
) -> Optional[str]:
    parts: list[str] = []
    if brand_norm:
        parts.append(brand_norm)
    if family:
        parts.append(family)
    if variant:
        parts.append(variant)
    if series_code:
        parts.append(series_code)
    parts.extend(trims)
    if gearbox:
        parts.append(f"({gearbox})")
    return " ".join(parts).strip() or None
