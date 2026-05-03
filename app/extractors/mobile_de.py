from __future__ import annotations

import re
from typing import Optional

from app.models import ExtractionResult, FieldExtraction
from app.normalizers import (
    normalize_first_registration,
    normalize_mileage,
    normalize_power_kw,
    normalize_displacement,
    normalize_previous_owners,
    normalize_price,
)

_PORTAL = "mobile.de"

# Patterns used against OCR-extracted text lines.
# mobile.de screenshots show label/value pairs like:
#   "Kilometerstand"  followed by  "19.600 km"
# The title line typically looks like:
#   "Honda GL 1800 | Goldwing Tour | ABS | Modell 2026 | für 39.990 €"

_LABEL_AFTER = [
    ("mileage", re.compile(r"Kilometerstand", re.I),
     re.compile(r"([\d\s\.\,]+\s*km)", re.I)),
    ("power", re.compile(r"Leistung", re.I),
     re.compile(r"([\d\s,\.]+\s*kW[\s\S]*?PS\))", re.I)),
    ("fuel", re.compile(r"Kraftstoffart|Antriebsart", re.I),
     re.compile(r"^(Benzin|Diesel|Elektro|Hybrid|Gas|LPG|CNG|Wasserstoff)", re.I)),
    ("transmission", re.compile(r"Getriebe", re.I),
     re.compile(r"^(Automatik|Schaltgetriebe|Manuell|Halbautomatik|CVT)", re.I)),
    ("first_reg", re.compile(r"Erstzulassung", re.I),
     re.compile(r"(\d{1,2}[/\-.]\d{4})")),
    ("owners", re.compile(r"Fahrzeughalter|Vorbesitzer", re.I),
     re.compile(r"^(\d+)")),
    ("color", re.compile(r"^Farbe$", re.I),
     re.compile(r"^(\w[\w\s]+?)$")),
    ("displacement", re.compile(r"Hubraum", re.I),
     re.compile(r"([\d\s\.\,]+\s*cm.{0,3}|[\d\s\.]+\s*ccm)", re.I)),
    ("condition", re.compile(r"Zustand", re.I),
     re.compile(r"^(\w[\w\s]*?)$")),
    ("location", re.compile(r"DE-\d{5}|^\d{5}\s+\w", re.I), None),
]

_PRICE_PATTERN = re.compile(r"([\d\.\,]+)\s*€", re.I)
_TITLE_PATTERN = re.compile(
    r"^(Honda|BMW|Yamaha|Kawasaki|Suzuki|Ducati|KTM|Triumph|Harley|Husqvarna"
    r"|Royal Enfield|Moto Guzzi|Aprilia|Benelli|Indian)\s+(.+?)(?:\s*\||\s+für|\s*$)",
    re.I,
)
_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:suchen\.)?mobile\.de/fahrzeuge/details[\w./=&?%-]*", re.I
)
_ID_FROM_URL = re.compile(r"[?&]id=(\d+)", re.I)


def extract(ocr_text: str) -> ExtractionResult:
    result = ExtractionResult(source_marketplace=_PORTAL)
    lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]

    result.url = _extract_url(lines)
    if result.url.value:
        m = _ID_FROM_URL.search(result.url.value)
        if m:
            result.listing_id = m.group(1)

    result.brand, result.model = _extract_brand_model(lines)
    result.price_amount, result.price_currency = _extract_price(lines)

    _extract_label_value_fields(lines, result)

    result.ocr_text = ocr_text
    result.vehicle_type = FieldExtraction("Motorbike", 0.8)
    return result


def _extract_url(lines: list[str]) -> FieldExtraction:
    for line in lines:
        m = _URL_PATTERN.search(line)
        if m:
            return FieldExtraction(m.group(), 1.0, line)
    return FieldExtraction(None, 0.0)


def _extract_brand_model(lines: list[str]) -> tuple[FieldExtraction, FieldExtraction]:
    for line in lines:
        m = _TITLE_PATTERN.match(line)
        if m:
            brand = m.group(1).strip()
            rest = m.group(2).strip()
            model_parts = [p.strip() for p in rest.split("|") if p.strip()]
            model = model_parts[0] if model_parts else rest
            return FieldExtraction(brand, 0.9, line), FieldExtraction(model, 0.8, line)
    return FieldExtraction(None, 0.0), FieldExtraction(None, 0.0)


def _extract_price(lines: list[str]) -> tuple[FieldExtraction, FieldExtraction]:
    for line in lines:
        m = _PRICE_PATTERN.search(line)
        if m:
            raw = m.group(1)
            val = normalize_price(raw + " €")
            if val and val > 100:
                return FieldExtraction(str(val), 0.9, line), FieldExtraction("EUR", 1.0)
    return FieldExtraction(None, 0.0), FieldExtraction(None, 0.0)


def _extract_label_value_fields(lines: list[str], result: ExtractionResult) -> None:
    for i, line in enumerate(lines):
        next_lines = lines[i + 1: i + 4]

        if re.search(r"Kilometerstand", line, re.I):
            for nxt in next_lines:
                raw = re.search(r"([\d\s\.\,]+)\s*km", nxt, re.I)
                if raw:
                    val = normalize_mileage(raw.group())
                    if val is not None:
                        result.mileage_km = FieldExtraction(str(val), 0.9, nxt)
                        break

        elif re.search(r"Leistung", line, re.I):
            for nxt in next_lines:
                val = normalize_power_kw(nxt)
                if val is not None:
                    result.power_kw = FieldExtraction(str(val), 0.9, nxt)
                    break

        elif re.search(r"Kraftstoffart|Antriebsart", line, re.I):
            for nxt in next_lines:
                m = re.match(r"(Benzin|Diesel|Elektro|Hybrid|Gas|LPG|CNG|Wasserstoff)", nxt, re.I)
                if m:
                    result.fuel_type = FieldExtraction(m.group(1), 0.9, nxt)
                    break

        elif re.search(r"^Getriebe$", line, re.I):
            for nxt in next_lines:
                m = re.match(r"(Automatik|Schaltgetriebe|Manuell|Halbautomatik|CVT)", nxt, re.I)
                if m:
                    result.transmission = FieldExtraction(m.group(1), 0.9, nxt)
                    break

        elif re.search(r"Erstzulassung", line, re.I):
            for nxt in next_lines:
                reg_str, year = normalize_first_registration(nxt)
                if reg_str:
                    result.first_registration = FieldExtraction(reg_str, 0.9, nxt)
                    if year and result.year.value is None:
                        result.year = FieldExtraction(str(year), 0.8, nxt)
                    break

        elif re.search(r"Fahrzeughalter|Vorbesitzer", line, re.I):
            for nxt in next_lines:
                val = normalize_previous_owners(nxt)
                if val is not None:
                    result.previous_owner_count = FieldExtraction(str(val), 0.9, nxt)
                    break

        elif re.search(r"^Farbe$", line, re.I):
            if next_lines:
                result.color = FieldExtraction(next_lines[0], 0.8, next_lines[0])

        elif re.search(r"Hubraum", line, re.I):
            for nxt in next_lines:
                val = normalize_displacement(nxt)
                if val is not None:
                    result.engine_displacement_cc = FieldExtraction(str(val), 0.85, nxt)
                    break

        elif re.search(r"^Zustand$", line, re.I):
            if next_lines:
                result.condition = FieldExtraction(next_lines[0], 0.8, next_lines[0])

        m_loc = re.search(r"DE-(\d{5})\s+(.+)", line)
        if m_loc and not result.location_city.value:
            result.location_city = FieldExtraction(m_loc.group(2).strip(), 0.8, line)
        elif re.match(r"\d{5}\s+\w", line) and not result.location_city.value:
            parts = line.split(None, 1)
            if len(parts) == 2:
                result.location_city = FieldExtraction(parts[1].strip(), 0.75, line)

    _try_extract_year_from_title(lines, result)


def _try_extract_year_from_title(lines: list[str], result: ExtractionResult) -> None:
    if result.year.value:
        return
    for line in lines:
        if re.search(r"Modell\s+(\d{4})", line, re.I):
            m = re.search(r"Modell\s+(\d{4})", line, re.I)
            if m:
                result.year = FieldExtraction(m.group(1), 0.75, line)
                return
