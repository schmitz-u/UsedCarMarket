"""Tests for SQLite persistence: dedup, upsert, price history."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import VehicleListing


@pytest.fixture()
def db():
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    import app.db as db_mod
    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = tmp
    db_mod.init_db(tmp)
    yield db_mod
    db_mod.DB_PATH = original_path
    if os.path.exists(tmp):
        os.unlink(tmp)


def make_listing(**kwargs):
    defaults = dict(
        source_marketplace="mobile.de",
        brand="Honda",
        model="CBR600",
        year=2020,
        mileage_km=15000,
        price_amount=8000.0,
        price_currency="EUR",
        url=None,
    )
    defaults.update(kwargs)
    return VehicleListing(**defaults)


class TestUpsertListing:
    def test_insert_new(self, db):
        listing = make_listing(url="https://example.com/1")
        row_id, action = db.upsert_listing(listing)
        assert action == "inserted"
        assert isinstance(row_id, int)

    def test_update_same_url(self, db):
        listing = make_listing(url="https://example.com/2")
        db.upsert_listing(listing)
        listing.price_amount = 7500.0
        _, action = db.upsert_listing(listing)
        assert action == "updated"

    def test_update_same_fingerprint_no_url(self, db):
        listing = make_listing()
        db.upsert_listing(listing)
        listing.price_amount = 7500.0
        _, action = db.upsert_listing(listing)
        assert action == "updated"

    def test_no_duplicate_listing_row(self, db):
        listing = make_listing(url="https://example.com/3")
        db.upsert_listing(listing)
        db.upsert_listing(listing)
        rows = db.query_listings(brand="Honda")
        urls = [r["url"] for r in rows if r["url"] == "https://example.com/3"]
        assert len(urls) == 1

    def test_price_history_appended_on_insert(self, db):
        listing = make_listing(url="https://example.com/4")
        row_id, _ = db.upsert_listing(listing)
        history = db.get_price_history(row_id)
        assert len(history) == 1
        assert history[0]["observed_price_amount"] == 8000.0

    def test_price_history_grows_on_update(self, db):
        listing = make_listing(url="https://example.com/5")
        row_id, _ = db.upsert_listing(listing)
        listing.price_amount = 7500.0
        db.upsert_listing(listing)
        history = db.get_price_history(row_id)
        assert len(history) == 2
        prices = sorted([h["observed_price_amount"] for h in history])
        assert prices == [7500.0, 8000.0]


class TestQueryListings:
    def test_filter_by_source(self, db):
        db.upsert_listing(make_listing(source_marketplace="mobile.de", url="https://a.com/1"))
        db.upsert_listing(make_listing(source_marketplace="autoscout24", url="https://b.com/1"))
        results = db.query_listings(source="mobile.de")
        assert all(r["source_marketplace"] == "mobile.de" for r in results)

    def test_filter_by_brand(self, db):
        db.upsert_listing(make_listing(brand="Yamaha", url="https://c.com/1"))
        results = db.query_listings(brand="Yamaha")
        assert any(r["brand"] == "Yamaha" for r in results)

    def test_filter_by_year_range(self, db):
        db.upsert_listing(make_listing(year=2015, url="https://d.com/1"))
        db.upsert_listing(make_listing(year=2022, url="https://d.com/2"))
        results = db.query_listings(year_min=2020, year_max=2025)
        years = [r["year"] for r in results]
        assert all(2020 <= y <= 2025 for y in years)

    def test_filter_by_price_range(self, db):
        db.upsert_listing(make_listing(price_amount=5000.0, url="https://e.com/1"))
        db.upsert_listing(make_listing(price_amount=15000.0, url="https://e.com/2"))
        results = db.query_listings(price_min=6000.0, price_max=20000.0)
        prices = [r["price_amount"] for r in results]
        assert all(p >= 6000.0 for p in prices)

    def test_seller_normalized_persisted_and_queryable(self, db):
        db.upsert_listing(
            make_listing(
                url="https://seller.com/1",
                condition="Händler",
                seller_normalized="Händler",
            )
        )
        results = db.query_listings()
        row = next(r for r in results if r["url"] == "https://seller.com/1")
        assert row["seller_normalized"] == "Händler"


class TestCheckExisting:
    def test_finds_by_url(self, db):
        listing = make_listing(url="https://f.com/1")
        row_id, _ = db.upsert_listing(listing)
        found = db.check_existing("https://f.com/1", "nope")
        assert found == row_id

    def test_finds_by_fingerprint(self, db):
        listing = make_listing()
        row_id, _ = db.upsert_listing(listing)
        from app.normalizers import generate_fingerprint
        fp = generate_fingerprint(listing.brand, listing.model, listing.year,
                                  listing.mileage_km, listing.price_amount)
        found = db.check_existing(None, fp)
        assert found == row_id

    def test_returns_none_when_absent(self, db):
        found = db.check_existing("https://notexist.com/99", "fakefp")
        assert found is None


class TestUpdateListingFields:
    def test_updates_selected_fields(self, db):
        listing = make_listing(url="https://edit.com/1", brand="Honda", model="Gold Wing")
        row_id, _ = db.upsert_listing(listing)

        row = db.update_listing_fields(
            row_id,
            {"brand": "BMW", "model": "R 1250 RT", "location_city": "Berlin"},
        )

        assert row is not None
        assert row["brand"] == "BMW"
        assert row["model"] == "R 1250 RT"
        assert row["location_city"] == "Berlin"

    def test_price_update_appends_manual_history(self, db):
        listing = make_listing(url="https://edit.com/2", price_amount=10000.0)
        row_id, _ = db.upsert_listing(listing)
        before = db.get_price_history(row_id)

        db.update_listing_fields(row_id, {"price_amount": 9500.0})
        after = db.get_price_history(row_id)

        assert len(after) == len(before) + 1
        assert after[-1]["observed_price_amount"] == 9500.0
        assert after[-1]["source_event_type"] == "manual_edit"
