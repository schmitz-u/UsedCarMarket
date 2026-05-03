"""Unit tests for portal-specific extractors using fixture text."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.extractors.mobile_de import extract as mobile_de_extract
from app.extractors.autoscout24 import extract as as24_extract
from app.extractors.registry import detect_and_extract


MOBILE_DE_TEXT = """\
Honda GL 1800 | Goldwing Tour | ABS | Modell 2026 | für 39.990 €
https://suchen.mobile.de/fahrzeuge/details.html?id=451777822&vc=Motorbike
Kilometerstand
0 km
Leistung
93 kW (126 PS)
Kraftstoffart
Benzin
Getriebe
Automatik
Erstzulassung
03/2026
Fahrzeughalter
1
Farbe
Rot Metallic Matt
Hubraum
1833 cm3
DE-47877 Willich
39.990 €
mobile.de
"""

AUTOSCOUT24_TEXT = """\
Honda Gold Wing Tourer in Orange gebraucht in Hameln, Stadt für € 12.000
https://www.autoscout24.de/angebote/honda-gold-wing-f6b-benzin-orange-f2cc2803-8151-403f-b483-680300ad25a8
Kilometerstand
19.600 km
Leistung
87 kW (118 PS)
Getriebe
Schaltgetriebe
Erstzulassung
04/2016
Hubraum
1830 cm3
Benzin
Farbe
Orange
Vorbesitzer
1
31789 Hameln, Stadt
€ 12.000
autoscout24
"""


class TestMobileDeExtractor:
    def setup_method(self):
        self.result = mobile_de_extract(MOBILE_DE_TEXT)

    def test_portal(self):
        assert self.result.source_marketplace == "mobile.de"

    def test_brand(self):
        assert self.result.brand.value == "Honda"

    def test_model(self):
        assert "GL" in self.result.model.value or "Goldwing" in self.result.model.value

    def test_mileage(self):
        assert self.result.mileage_km.value == "0"

    def test_price(self):
        assert self.result.price_amount.value == "39990.0"

    def test_price_currency(self):
        assert self.result.price_currency.value == "EUR"

    def test_fuel(self):
        assert self.result.fuel_type.value == "Benzin"

    def test_transmission(self):
        assert self.result.transmission.value == "Automatik"

    def test_first_registration(self):
        assert self.result.first_registration.value == "03/2026"

    def test_year(self):
        assert self.result.year.value == "2026"

    def test_owners(self):
        assert self.result.previous_owner_count.value == "1"

    def test_color(self):
        assert "Rot" in (self.result.color.value or "")

    def test_displacement(self):
        assert self.result.engine_displacement_cc.value == "1833"

    def test_power_kw(self):
        assert self.result.power_kw.value == "93.0"

    def test_url(self):
        assert "mobile.de" in (self.result.url.value or "")
        assert "451777822" in (self.result.url.value or "")

    def test_listing_id(self):
        assert self.result.listing_id == "451777822"

    def test_location(self):
        assert "Willich" in (self.result.location_city.value or "")

    def test_overall_confidence_positive(self):
        assert self.result.overall_confidence() > 0.5


class TestAutoScout24Extractor:
    def setup_method(self):
        self.result = as24_extract(AUTOSCOUT24_TEXT)

    def test_portal(self):
        assert self.result.source_marketplace == "autoscout24"

    def test_brand(self):
        assert self.result.brand.value == "Honda"

    def test_model(self):
        assert "Gold Wing" in (self.result.model.value or "")

    def test_mileage(self):
        assert self.result.mileage_km.value == "19600"

    def test_price(self):
        assert self.result.price_amount.value == "12000.0"

    def test_price_currency(self):
        assert self.result.price_currency.value == "EUR"

    def test_fuel(self):
        assert self.result.fuel_type.value == "Benzin"

    def test_transmission(self):
        assert self.result.transmission.value == "Schaltgetriebe"

    def test_first_registration(self):
        assert self.result.first_registration.value == "04/2016"

    def test_year(self):
        assert self.result.year.value == "2016"

    def test_owners(self):
        assert self.result.previous_owner_count.value == "1"

    def test_color(self):
        assert self.result.color.value == "Orange"

    def test_displacement(self):
        assert self.result.engine_displacement_cc.value == "1830"

    def test_power_kw(self):
        assert self.result.power_kw.value == "87.0"

    def test_url(self):
        assert "autoscout24.de" in (self.result.url.value or "")

    def test_listing_id(self):
        assert "f2cc2803" in (self.result.listing_id or "")

    def test_location(self):
        assert "Hameln" in (self.result.location_city.value or "")

    def test_overall_confidence_positive(self):
        assert self.result.overall_confidence() > 0.5


class TestRegistry:
    def test_detects_mobile_de(self):
        result = detect_and_extract(MOBILE_DE_TEXT)
        assert result.source_marketplace == "mobile.de"

    def test_detects_autoscout24(self):
        result = detect_and_extract(AUTOSCOUT24_TEXT)
        assert result.source_marketplace == "autoscout24"

    def test_unknown_text_returns_best_guess(self):
        result = detect_and_extract("Some vehicle for sale. Price: 5.000 €.")
        assert result is not None


class TestToVehicleListing:
    def test_mobile_de_to_listing(self):
        result = mobile_de_extract(MOBILE_DE_TEXT)
        listing = result.to_vehicle_listing()
        assert listing.brand == "Honda"
        assert listing.price_amount == 39990.0
        assert listing.mileage_km == 0
        assert listing.year == 2026

    def test_autoscout24_to_listing(self):
        result = as24_extract(AUTOSCOUT24_TEXT)
        listing = result.to_vehicle_listing()
        assert listing.brand == "Honda"
        assert listing.price_amount == 12000.0
        assert listing.mileage_km == 19600
        assert listing.year == 2016
