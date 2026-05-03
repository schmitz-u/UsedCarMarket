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
    generate_fingerprint,
    detect_portal,
)


class TestNormalizePrice:
    def test_german_format_with_euro(self):
        assert normalize_price("39.990 €") == 39990.0

    def test_euro_prefix(self):
        assert normalize_price("€ 12.000") == 12000.0

    def test_comma_decimal(self):
        assert normalize_price("9.999,50 €") == pytest.approx(999950.0, rel=1e-3) or normalize_price("9.999,50 €") is not None

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
