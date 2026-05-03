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
            "Honda", "CBR", 2022, 5000, 8000.0,
        )
        resp = client.post("/api/save", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "inserted"
        assert isinstance(data["id"], int)

    def test_save_same_url_returns_updated(self, client):
        url = "https://suchen.mobile.de/fahrzeuge/details.html?id=999002"
        payload = self._make_save_payload("mobile.de", url, "BMW", "R1200", 2020, 10000, 12000.0)
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


class TestLogsEndpoint:
    def test_logs_returns_array(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_export_logs_returns_json_file(self, client):
        resp = client.get("/api/logs/export")
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
