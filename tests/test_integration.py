"""Integration tests: upload -> review payload -> save -> analysis refresh."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point the DB to a temporary file before importing app.main
_tmpdir = tempfile.mkdtemp()
_test_db_path = os.path.join(_tmpdir, "test.db")
os.environ["UCM_DB_PATH"] = _test_db_path

import app.db as db_module

db_module.DB_PATH = _test_db_path
db_module.init_db(_test_db_path)

from app.main import application
from fastapi.testclient import TestClient

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def client():
    with TestClient(application) as c:
        yield c


def _upload_fixture(client, filename: str):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "rb") as f:
        resp = client.post("/api/upload", files={"file": (filename, f, "image/png")})
    return resp


class TestUploadEndpoint:
    def test_upload_mobile_de_fixture_returns_200(self, client):
        resp = _upload_fixture(client, "mobile_de_sample.png")
        assert resp.status_code == 200

    def test_upload_response_has_fields(self, client):
        resp = _upload_fixture(client, "mobile_de_sample.png")
        data = resp.json()
        assert "fields" in data
        assert "overall_confidence" in data
        assert "image_hash" in data

    def test_upload_wrong_type_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_autoscout24_fixture_returns_200(self, client):
        resp = _upload_fixture(client, "autoscout24_sample.png")
        assert resp.status_code == 200


class TestSaveEndpoint:
    def _make_save_payload(self, portal, url, brand, model, year, km, price):
        return {
            "portal": portal,
            "image_hash": "aabbcc",
            "filename": "test.png",
            "fields": {
                "url": {"value": url, "confidence": 1.0},
                "brand": {"value": brand, "confidence": 0.9},
                "model": {"value": model, "confidence": 0.9},
                "year": {"value": str(year), "confidence": 0.9},
                "mileage_km": {"value": str(km), "confidence": 0.9},
                "price_amount": {"value": str(price), "confidence": 0.9},
                "price_currency": {"value": "EUR", "confidence": 1.0},
                "fuel_type": {"value": "Benzin", "confidence": 0.9},
                "transmission": {"value": "Automatik", "confidence": 0.9},
            },
        }

    def test_save_new_listing_returns_inserted(self, client):
        payload = self._make_save_payload(
            "mobile.de",
            "https://suchen.mobile.de/fahrzeuge/details.html?id=999001",
            "Honda",
            "CBR",
            2022,
            5000,
            8000.0,
        )
        resp = client.post("/api/save", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "inserted"
        assert isinstance(data["id"], int)

    def test_save_same_url_returns_updated(self, client):
        url = "https://suchen.mobile.de/fahrzeuge/details.html?id=999002"
        payload = self._make_save_payload(
            "mobile.de", url, "BMW", "R1200", 2020, 10000, 12000.0
        )
        client.post("/api/save", json=payload)
        resp = client.post("/api/save", json=payload)
        assert resp.status_code == 200
        assert resp.json()["action"] == "updated"

    def test_save_without_url_or_brand_rejected(self, client):
        payload = {
            "portal": "mobile.de",
            "image_hash": "xx",
            "filename": "x.png",
            "fields": {},
        }
        resp = client.post("/api/save", json=payload)
        assert resp.status_code in (400, 422)


class TestListingsEndpoint:
    def test_list_returns_array(self, client):
        resp = client.get("/api/listings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_brand(self, client):
        url = "https://suchen.mobile.de/fahrzeuge/details.html?id=999003"
        payload = {
            "portal": "mobile.de",
            "image_hash": "dd",
            "filename": "x.png",
            "fields": {
                "url": {"value": url, "confidence": 1.0},
                "brand": {"value": "Yamaha", "confidence": 0.9},
                "price_amount": {"value": "7000", "confidence": 0.9},
            },
        }
        client.post("/api/save", json=payload)
        resp = client.get("/api/listings?brand=Yamaha")
        assert any(r["brand"] == "Yamaha" for r in resp.json())

    def test_list_returns_seller_normalized(self, client):
        url = "https://suchen.mobile.de/fahrzeuge/details.html?id=999004"
        payload = {
            "portal": "mobile.de",
            "image_hash": "ee",
            "filename": "x.png",
            "fields": {
                "url": {"value": url, "confidence": 1.0},
                "brand": {"value": "Honda", "confidence": 1.0},
                "model": {"value": "Gold Wing", "confidence": 1.0},
                "condition": {"value": "Privat", "confidence": 1.0},
                "price_amount": {"value": "10000", "confidence": 1.0},
            },
        }
        save_resp = client.post("/api/save", json=payload)
        assert save_resp.status_code == 200

        rows = client.get("/api/listings").json()
        row = next((r for r in rows if r["url"] == url), None)
        assert row is not None
        assert row["seller_normalized"] == "Privat"


class TestUpdateListingEndpoint:
    def test_update_listing_edits_table_fields(self, client):
        create_payload = {
            "portal": "autoscout24",
            "image_hash": "upd-1",
            "filename": "x.png",
            "fields": {
                "url": {"value": "https://example.com/edit-1", "confidence": 1.0},
                "brand": {"value": "Honda", "confidence": 1.0},
                "model": {"value": "Gold Wing", "confidence": 1.0},
                "year": {"value": "2020", "confidence": 1.0},
                "mileage_km": {"value": "30000", "confidence": 1.0},
                "price_amount": {"value": "20000", "confidence": 1.0},
            },
        }
        save_resp = client.post("/api/save", json=create_payload)
        assert save_resp.status_code == 200
        listing_id = save_resp.json()["id"]

        update_resp = client.put(
            f"/api/listings/{listing_id}",
            json={
                "brand": "Honda",
                "model": "GL 1800",
                "year": 2023,
                "mileage_km": 12000,
                "price_amount": 23990,
                "seller_normalized": "Händler",
            },
        )
        assert update_resp.status_code == 200

        rows = client.get("/api/listings").json()
        row = next((r for r in rows if r["id"] == listing_id), None)
        assert row is not None
        assert row["model"] == "GL 1800"
        assert row["year"] == 2023
        assert row["mileage_km"] == 12000
        assert row["price_amount"] == 23990
        assert row["seller_normalized"] == "Händler"

    def test_update_listing_rejects_harmonization_conflict(self, client):
        create_payload = {
            "portal": "autoscout24",
            "image_hash": "upd-2",
            "filename": "x.png",
            "fields": {
                "url": {"value": "https://example.com/edit-2", "confidence": 1.0},
                "brand": {"value": "Honda", "confidence": 1.0},
                "model": {"value": "Gold Wing", "confidence": 1.0},
                "year": {"value": "2020", "confidence": 1.0},
                "price_amount": {"value": "20000", "confidence": 1.0},
            },
        }
        save_resp = client.post("/api/save", json=create_payload)
        assert save_resp.status_code == 200
        listing_id = save_resp.json()["id"]

        # GL1500 is incompatible with 2024 and must fail with 422.
        update_resp = client.put(
            f"/api/listings/{listing_id}",
            json={"model": "GL1500", "year": 2024},
        )
        assert update_resp.status_code == 422


class TestLogsEndpoint:
    def test_logs_returns_array(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_export_logs_returns_json_file(self, client):
        resp = client.get("/api/logs/export")
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")


class TestImageStorageAndPreview:
    def test_saved_listing_exposes_image_url_and_image_endpoint(self, client):
        upload_resp = _upload_fixture(client, "mobile_de_sample.png")
        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()

        fields = upload_data.get("fields", {})
        if not (
            fields.get("url", {}).get("value") or fields.get("brand", {}).get("value")
        ):
            fields["brand"] = {"value": "Honda", "confidence": 1.0}

        save_payload = {
            "portal": upload_data.get("portal"),
            "image_hash": upload_data.get("image_hash"),
            "filename": upload_data.get("filename"),
            "fields": fields,
        }
        save_resp = client.post("/api/save", json=save_payload)
        assert save_resp.status_code == 200
        listing_id = save_resp.json()["id"]

        list_resp = client.get("/api/listings")
        assert list_resp.status_code == 200
        rows = list_resp.json()
        row = next((r for r in rows if r["id"] == listing_id), None)
        assert row is not None
        assert row["has_image"] is True
        assert row["image_url"] == f"/api/listings/{listing_id}/image"

        image_resp = client.get(row["image_url"])
        assert image_resp.status_code == 200
        assert image_resp.headers.get("content-type", "").startswith("image/")
        assert len(image_resp.content) > 0
