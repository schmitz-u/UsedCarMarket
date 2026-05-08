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

_PORTAL = "autoscout24"

# AutoScout24 screenshots show label/value pairs similar to:
#   "Kilometerstand"  "19.600 km"
#   "Leistung"        "87 kW (118 PS)"
#   "Getriebe"        (value on same or next line)
#   "Erstzulassung"   (value on same or next line)
# Price appears as "€ 12.000" or "€12.000"
# Title: "Honda Gold Wing Tourer in Orange gebraucht in Hameln, Stadt für € 12.000"

_PRICE_PATTERN = re.compile(r"€\s*([\d\.\,]+)", re.I)
_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?autoscout24\.de/angebote/[\w\-]+", re.I
)
_TITLE_PATTERN = re.compile(
    r"^(Honda|BMW|Yamaha|Kawasaki|Suzuki|Ducati|KTM|Triumph|Harley|Husqvarna"
    r"|Royal Enfield|Moto Guzzi|Aprilia|Benelli|Indian|Mercedes|Volkswagen|VW"
    r"|Audi|Ford|Opel|Toyota|Mazda|Volvo|Seat|Skoda|Renault|Peugeot|Citroën"
    r"|Fiat|Alfa|Porsche)\s+(.+?)(?:\s+in\s+|\s+für\s+|\s*$)",
    re.I,
)
_ID_FROM_URL = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I
)
_LOCATION_PATTERN = re.compile(r"(\d{5})\s+([\w\s,\-]+?)(?:,\s*DE\b|$)", re.I)
_CITY_PIN_PATTERN = re.compile(
    r"©\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s,\-\.]{1,60})\s*\|", re.I
)
_FUEL_PATTERN = re.compile(
    r"\b(Benzin|Diesel|Elektro|Hybrid|Gas|LPG|CNG|Wasserstoff)\b", re.I
)
_TRANSMISSION_PATTERN = re.compile(
    r"\b(Automatik|Schaltgetriebe|Manuell|Halbautomatik|CVT|DCT)\b", re.I
)
_SELLER_PATTERN = re.compile(r"\b(Händler|Haendler|Handler|Privat|Gewerblich)\b", re.I)
_CITY_BLACKLIST = {"CHECK24", "Drucken", "Gemerkt", "Teilen", "Vergleichen"}
_FUEL_CANONICAL = {
    "benzin": "Benzin",
    "diesel": "Diesel",
    "elektro": "Elektro",
    "hybrid": "Hybrid",
    "gas": "Gas",
    "lpg": "LPG",
    "cng": "CNG",
    "wasserstoff": "Wasserstoff",
}


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
            model_parts = rest.split()
            model = " ".join(model_parts[:3]) if model_parts else rest
            return FieldExtraction(brand, 0.9, line), FieldExtraction(model, 0.8, line)
    return FieldExtraction(None, 0.0), FieldExtraction(None, 0.0)


def _extract_price(lines: list[str]) -> tuple[FieldExtraction, FieldExtraction]:
    for line in lines:
        m = _PRICE_PATTERN.search(line)
        if m:
            raw = m.group(1)
            val = normalize_price(raw)
            if val and val > 100:
                return FieldExtraction(str(val), 0.9, line), FieldExtraction("EUR", 1.0)
    return FieldExtraction(None, 0.0), FieldExtraction(None, 0.0)


def _canon_fuel(raw: str) -> str:
    return _FUEL_CANONICAL.get(raw.lower(), raw)


def _extract_label_value_fields(lines: list[str], result: ExtractionResult) -> None:
    for i, line in enumerate(lines):
        next_lines = lines[i + 1 : i + 4]

        if re.search(r"Kilometerstand", line, re.I):
            for nxt in next_lines:
                raw = re.search(r"([\d\s\.\,]+)\s*km", nxt, re.I)
                if raw:
                    val = normalize_mileage(raw.group())
                    if val is not None:
                        result.mileage_km = FieldExtraction(str(val), 0.9, nxt)
                        break
            if not result.mileage_km.value:
                m = re.search(r"([\d\s\.\,]+)\s*km", line, re.I)
                if m:
                    val = normalize_mileage(m.group())
                    if val is not None:
                        result.mileage_km = FieldExtraction(str(val), 0.85, line)

        if re.search(r"Leistung", line, re.I):
            for nxt in next_lines:
                val = normalize_power_kw(nxt)
                if val is not None:
                    result.power_kw = FieldExtraction(str(val), 0.9, nxt)
                    break
            if not result.power_kw.value:
                val = normalize_power_kw(line)
                if val is not None:
                    result.power_kw = FieldExtraction(str(val), 0.85, line)

        if re.search(r"Kraftstoff|Antriebsart", line, re.I):
            for nxt in next_lines:
                m = _FUEL_PATTERN.search(nxt)
                if m:
                    result.fuel_type = FieldExtraction(_canon_fuel(m.group(1)), 0.9, nxt)
                    break
            if not result.fuel_type.value:
                m = _FUEL_PATTERN.search(line)
                if m:
                    result.fuel_type = FieldExtraction(
                        _canon_fuel(m.group(1)), 0.85, line
                    )

        if re.search(r"\bGetriebe\b", line, re.I):
            for nxt in next_lines:
                m = _TRANSMISSION_PATTERN.search(nxt)
                if m:
                    result.transmission = FieldExtraction(m.group(1), 0.9, nxt)
                    break
            if not result.transmission.value:
                m = _TRANSMISSION_PATTERN.search(line)
                if m:
                    result.transmission = FieldExtraction(m.group(1), 0.85, line)

        if re.search(r"Erstzulassung", line, re.I):
            for nxt in next_lines:
                reg_str, year = normalize_first_registration(nxt)
                if reg_str:
                    result.first_registration = FieldExtraction(reg_str, 0.9, nxt)
                    if year and result.year.value is None:
                        result.year = FieldExtraction(str(year), 0.8, nxt)
                    break
            if not result.first_registration.value:
                reg_str, year = normalize_first_registration(line)
                if reg_str:
                    result.first_registration = FieldExtraction(reg_str, 0.85, line)
                    if year and result.year.value is None:
                        result.year = FieldExtraction(str(year), 0.75, line)

        if re.search(r"Verkäufer|Verkaufer", line, re.I):
            for nxt in next_lines:
                m = _SELLER_PATTERN.search(nxt)
                if m:
                    label = (
                        "Händler"
                        if re.search(
                            r"h[aä]ndler|haendler|gewerblich", m.group(1), re.I
                        )
                        else "Privat"
                    )
                    result.seller_type = FieldExtraction(label, 0.9, nxt)
                    break
            if not result.seller_type.value:
                m = _SELLER_PATTERN.search(line)
                if m:
                    label = (
                        "Händler"
                        if re.search(
                            r"h[aä]ndler|haendler|gewerblich", m.group(1), re.I
                        )
                        else "Privat"
                    )
                    result.seller_type = FieldExtraction(label, 0.85, line)

        elif re.search(r"Vorbesitzer|Fahrzeughalter|Besitzer", line, re.I):
            for nxt in next_lines:
                val = normalize_previous_owners(nxt)
                if val is not None:
                    result.previous_owner_count = FieldExtraction(str(val), 0.9, nxt)
                    break

        elif re.search(r"Hubraum", line, re.I):
            for nxt in next_lines:
                val = normalize_displacement(nxt)
                if val is not None:
                    result.engine_displacement_cc = FieldExtraction(str(val), 0.85, nxt)
                    break
            if not result.engine_displacement_cc.value:
                val = normalize_displacement(line)
                if val is not None:
                    result.engine_displacement_cc = FieldExtraction(str(val), 0.8, line)

        elif re.search(r"^Farbe$", line, re.I):
            if next_lines:
                result.color = FieldExtraction(next_lines[0], 0.8, next_lines[0])

        elif re.search(r"^Zustand$", line, re.I):
            if next_lines:
                result.condition = FieldExtraction(next_lines[0], 0.8, next_lines[0])

        m_loc = _LOCATION_PATTERN.search(line)
        if m_loc and not result.location_city.value:
            city = m_loc.group(2).strip().rstrip(",")
            result.location_city = FieldExtraction(city, 0.8, line)

        if not result.location_city.value:
            m_pin = _CITY_PIN_PATTERN.search(line)
            if m_pin:
                city = m_pin.group(1).strip().rstrip(",")
                city = re.sub(r",\s*(Stadt|Kreis)\b", "", city, flags=re.I).strip()
                if 2 <= len(city) <= 60 and city not in _CITY_BLACKLIST:
                    result.location_city = FieldExtraction(city, 0.85, line)

        if not result.fuel_type.value:
            m = _FUEL_PATTERN.search(line)
            if m:
                result.fuel_type = FieldExtraction(_canon_fuel(m.group(1)), 0.7, line)

        if not result.transmission.value:
            m = _TRANSMISSION_PATTERN.search(line)
            if m:
                result.transmission = FieldExtraction(m.group(1), 0.7, line)

        if not result.seller_type.value:
            m = _SELLER_PATTERN.search(line)
            if m:
                label = (
                    "Händler"
                    if re.search(r"h[aä]ndler|haendler|gewerblich", m.group(1), re.I)
                    else "Privat"
                )
                result.seller_type = FieldExtraction(label, 0.7, line)

    _try_extract_from_title(lines, result)


def _try_extract_from_title(lines: list[str], result: ExtractionResult) -> None:
    for line in lines:
        if not result.color.value:
            m = re.search(
                r"\bin\s+(Schwarz|Weiß|Blau|Rot|Grün|Orange|Grau|Silber|Gelb|Braun|"
                r"Beige|Bordeaux|Bronze|Gold|Lila|Pink|Türkis)\b",
                line,
                re.I,
            )
            if m:
                result.color = FieldExtraction(m.group(1), 0.75, line)

        if not result.year.value:
            m = re.search(r"\b(20\d{2}|19\d{2})\b", line)
            if m:
                result.year = FieldExtraction(m.group(1), 0.65, line)

        if not result.location_city.value:
            m = re.search(
                r"\bin\s+([\w\s,\-]+?)(?:,\s*Stadt|,\s*Kreis|\s+für\s+|\s*$)",
                line,
                re.I,
            )
            if m:
                city = m.group(1).strip().rstrip(",")
                if 3 <= len(city) <= 60:
                    result.location_city = FieldExtraction(city, 0.7, line)
