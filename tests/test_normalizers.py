"""Unit tests for field normalizers."""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.normalizers import (
    normalize_price,
    normalize_mileage,
    normalize_power_kw,
    normalize_displacement,
    normalize_first_registration,
    normalize_previous_owners,
    normalize_seller_type,
    generate_fingerprint,
    detect_portal,
    harmonize_listing_title,
    validate_harmonized_listing,
    HarmonizationConflict,
)


class TestNormalizePrice:
    def test_german_format_with_euro(self):
        assert normalize_price("39.990 €") == 39990.0

    def test_euro_prefix(self):
        assert normalize_price("€ 12.000") == 12000.0

    def test_comma_decimal(self):
        assert normalize_price("9.999,50 €") == pytest.approx(9999.5, rel=1e-3)

    def test_plain_number(self):
        assert normalize_price("12000") == 12000.0

    def test_empty_returns_none(self):
        assert normalize_price("") is None
        assert normalize_price(None) is None


class TestNormalizeMileage:
    def test_german_format(self):
        assert normalize_mileage("19.600 km") == 19600

    def test_zero(self):
        assert normalize_mileage("0 km") == 0

    def test_nbsp_km(self):
        assert normalize_mileage("0\xa0km") == 0

    def test_empty_returns_none(self):
        assert normalize_mileage("") is None

    def test_no_unit(self):
        assert normalize_mileage("50000") == 50000


class TestNormalizePowerKw:
    def test_kw_ps_format(self):
        assert normalize_power_kw("93 kW (126 PS)") == 93.0

    def test_decimal_kw(self):
        assert normalize_power_kw("87,5 kW") == 87.5

    def test_no_kw_returns_none(self):
        assert normalize_power_kw("126 PS") is None

    def test_empty_returns_none(self):
        assert normalize_power_kw("") is None


class TestNormalizeDisplacement:
    def test_cm3_format(self):
        assert normalize_displacement("1.833 cm3") == 1833

    def test_ccm_format(self):
        assert normalize_displacement("1830 ccm") == 1830

    def test_too_small_returns_none(self):
        assert normalize_displacement("5") is None

    def test_empty_returns_none(self):
        assert normalize_displacement("") is None


class TestNormalizeFirstRegistration:
    def test_slash_format(self):
        reg, year = normalize_first_registration("03/2026")
        assert reg == "03/2026"
        assert year == 2026

    def test_dot_format(self):
        reg, year = normalize_first_registration("04.2016")
        assert reg == "04/2016"
        assert year == 2016

    def test_year_only(self):
        reg, year = normalize_first_registration("2020")
        assert reg == "2020"
        assert year == 2020

    def test_empty_returns_none(self):
        reg, year = normalize_first_registration("")
        assert reg is None
        assert year is None


class TestNormalizePreviousOwners:
    def test_single_digit(self):
        assert normalize_previous_owners("1") == 1

    def test_with_text(self):
        assert normalize_previous_owners("2 Besitzer") == 2

    def test_empty_returns_none(self):
        assert normalize_previous_owners("") is None


class TestNormalizeSellerType:
    def test_dealer_labels_to_haendler(self):
        assert normalize_seller_type("Händler") == "Händler"
        assert normalize_seller_type("gewerblicher Anbieter") == "Händler"
        assert normalize_seller_type("Dealer") == "Händler"

    def test_private_labels_to_privat(self):
        assert normalize_seller_type("Privat") == "Privat"
        assert normalize_seller_type("Privatanbieter") == "Privat"

    def test_unknown_returns_none(self):
        assert normalize_seller_type("Unbekannt") is None
        assert normalize_seller_type("") is None


class TestGenerateFingerprint:
    def test_deterministic(self):
        fp1 = generate_fingerprint("Honda", "Gold Wing", 2016, 19600, 12000.0)
        fp2 = generate_fingerprint("Honda", "Gold Wing", 2016, 19600, 12000.0)
        assert fp1 == fp2

    def test_different_inputs_differ(self):
        fp1 = generate_fingerprint("Honda", "Gold Wing", 2016, 19600)
        fp2 = generate_fingerprint("Honda", "Gold Wing", 2016, 20000)
        assert fp1 != fp2

    def test_case_insensitive(self):
        fp1 = generate_fingerprint("honda", "gold wing", 2016, 19600, 12000.0)
        fp2 = generate_fingerprint("Honda", "Gold Wing", 2016, 19600, 12000.0)
        assert fp1 == fp2

    def test_none_fields(self):
        fp = generate_fingerprint(None, None, None, None, None)
        assert isinstance(fp, str) and len(fp) == 32


class TestDetectPortal:
    def test_detect_mobile_de(self):
        assert detect_portal("mobile.de listing text") == "mobile.de"

    def test_detect_autoscout24(self):
        assert detect_portal("autoscout24 listing text") == "autoscout24"

    def test_unknown_returns_none(self):
        assert detect_portal("random text without portal info") is None


class TestHarmonizeListingTitle:
    def test_gl1800_bagger_top(self):
        out = harmonize_listing_title("Honda", "GL1800 Bagger TOP")
        assert out["brand_normalized"] == "Honda"
        assert out["model_family_normalized"] == "Gold Wing"
        assert out["model_variant_normalized"] == "GL 1800"
        assert out["trim_normalized"] == "Bagger"
        assert out["marketing_tags_json"] == "TOP"

    def test_f6b(self):
        out = harmonize_listing_title("Honda", "F6B")
        assert out["model_family_normalized"] == "Gold Wing"
        assert out["trim_normalized"] == "F6B / Bagger"

    def test_goldwing_bagger_dct_1_hand(self):
        out = harmonize_listing_title("Honda", "Goldwing Bagger DCT 1. Hand")
        assert out["model_family_normalized"] == "Gold Wing"
        assert out["trim_normalized"] == "Bagger"
        assert out["drivetrain_or_gearbox_normalized"] == "DCT"
        assert out["ownership_hint"] == "1. Hand"

    def test_1800_f6b(self):
        out = harmonize_listing_title("Honda", "1800 F6B")
        assert out["model_family_normalized"] == "Gold Wing"
        assert out["model_variant_normalized"] == "GL 1800"
        assert out["trim_normalized"] == "F6B / Bagger"

    def test_f6b_with_gold_wing_bagger_in_parentheses(self):
        out = harmonize_listing_title("Honda", "F6B (Gold Wing Bagger)")
        assert out["model_family_normalized"] == "Gold Wing"
        assert out["trim_normalized"] == "F6B / Bagger"
        assert out["title_harmonized"] == "Honda Gold Wing F6B Bagger"

    def test_year_infers_gl1500(self):
        out = harmonize_listing_title("Honda", "Gold Wing", year=1995)
        assert out["model_variant_normalized"] == "GL 1500"

    def test_year_infers_gl1800(self):
        out = harmonize_listing_title("Honda", "Gold Wing", year=2022)
        assert out["model_variant_normalized"] == "GL 1800"

    def test_bagger_2014_enriches_to_f6b(self):
        out = harmonize_listing_title("Honda", "Gold Wing Bagger", year=2014)
        assert out["trim_normalized"] == "F6B / Bagger"

    def test_tourer_normalizes_to_tour(self):
        out = harmonize_listing_title("Honda", "Gold Wing Tourer")
        assert out["trim_normalized"] == "Tour"

    def test_condition_normalizes_seller_dealer(self):
        out = harmonize_listing_title("Honda", "Gold Wing", condition="Händler")
        assert out["seller_normalized"] == "Händler"

    def test_condition_normalizes_seller_private(self):
        out = harmonize_listing_title("Honda", "Gold Wing", condition="Privat")
        assert out["seller_normalized"] == "Privat"


class TestValidateHarmonizedListing:
    def _h(self, model_fragment, year=None):
        h = harmonize_listing_title("Honda", model_fragment, year=year)
        return h, year

    def test_valid_gl1800_passes(self):
        h, y = self._h("GL 1800", year=2020)
        validate_harmonized_listing(h, y)  # must not raise

    def test_valid_gl1500_passes(self):
        h, y = self._h("Gold Wing GL1500", year=1995)
        validate_harmonized_listing(h, y)

    def test_gl1500_with_modern_year_raises(self):
        h, y = self._h("Gold Wing GL1500", year=2024)
        with pytest.raises(HarmonizationConflict, match="GL 1500"):
            validate_harmonized_listing(h, y)

    def test_gl1800_with_pre_2001_year_raises(self):
        h, y = self._h("GL 1800", year=1999)
        with pytest.raises(HarmonizationConflict, match="GL 1800"):
            validate_harmonized_listing(h, y)

    def test_f6b_with_pre_2013_year_raises(self):
        h = harmonize_listing_title("Honda", "F6B", year=2010)
        with pytest.raises(HarmonizationConflict, match="F6B"):
            validate_harmonized_listing(h, 2010)

    def test_f6b_after_2016_raises(self):
        h = harmonize_listing_title("Honda", "F6B", year=2019)
        with pytest.raises(HarmonizationConflict, match="F6B"):
            validate_harmonized_listing(h, 2019)

    def test_dct_before_2018_raises(self):
        h = harmonize_listing_title("Honda", "Gold Wing DCT", year=2015)
        with pytest.raises(HarmonizationConflict, match="DCT"):
            validate_harmonized_listing(h, 2015)

    def test_dct_2018_passes(self):
        h = harmonize_listing_title("Honda", "Gold Wing DCT", year=2018)
        validate_harmonized_listing(h, 2018)  # must not raise

    def test_missing_year_always_passes(self):
        h = harmonize_listing_title("Honda", "GL 1800")
        validate_harmonized_listing(h, None)  # must not raise
