from __future__ import annotations

import hashlib
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import app.logger as ops_logger
from app.db import (
    check_existing,
    get_price_history,
    init_db,
    query_listings,
    upsert_listing,
)
from app.extractors import detect_and_extract
from app.models import VehicleListing
from app.normalizers import generate_fingerprint
from app.ocr import run_ocr_from_bytes

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("UCM_DB_PATH", "used_car_market.db")
    init_db(db_path)
    yield


application = FastAPI(title="Used Car Market Analyzer", lifespan=lifespan)

application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@application.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@application.post("/api/upload")
async def upload_screenshot(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Accept a screenshot upload, run OCR, extract fields, and return the
    extraction result for the review form.
    """
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use PNG or JPEG.",
        )

    data = await file.read()
    image_hash = hashlib.sha256(data).hexdigest()

    ocr_text = run_ocr_from_bytes(data)

    extraction = detect_and_extract(ocr_text)
    extraction.ocr_text = ocr_text

    ops_logger.log_upload(file.filename or "", image_hash, extraction.source_marketplace)
    ops_logger.log_ocr(image_hash, len(ocr_text), extraction.overall_confidence())

    listing = extraction.to_vehicle_listing()
    fingerprint = generate_fingerprint(
        listing.brand, listing.model, listing.year,
        listing.mileage_km, listing.price_amount,
    )

    existing_id = check_existing(listing.url, fingerprint)

    return {
        "image_hash": image_hash,
        "filename": file.filename,
        "portal": extraction.source_marketplace,
        "existing_id": existing_id,
        "overall_confidence": extraction.overall_confidence(),
        "fields": {
            "url": _fe(extraction.url),
            "brand": _fe(extraction.brand),
            "model": _fe(extraction.model),
            "year": _fe(extraction.year),
            "first_registration": _fe(extraction.first_registration),
            "mileage_km": _fe(extraction.mileage_km),
            "previous_owner_count": _fe(extraction.previous_owner_count),
            "price_amount": _fe(extraction.price_amount),
            "price_currency": _fe(extraction.price_currency),
            "engine_displacement_cc": _fe(extraction.engine_displacement_cc),
            "power_kw": _fe(extraction.power_kw),
            "fuel_type": _fe(extraction.fuel_type),
            "transmission": _fe(extraction.transmission),
            "color": _fe(extraction.color),
            "vehicle_category": _fe(extraction.vehicle_category),
            "vehicle_type": _fe(extraction.vehicle_type),
            "location_city": _fe(extraction.location_city),
            "condition": _fe(extraction.condition),
        },
    }


def _fe(fe: Any) -> dict[str, Any]:
    return {"value": fe.value, "confidence": fe.confidence}


@application.post("/api/save")
async def save_listing(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Save (insert or update) a reviewed listing to SQLite.
    Expects the JSON body to contain the corrected field values.
    """
    fields = payload.get("fields", {})
    image_hash = payload.get("image_hash")
    filename = payload.get("filename")

    def _get(name: str) -> Optional[str]:
        v = fields.get(name, {})
        if isinstance(v, dict):
            return v.get("value")
        return v

    def _to_float(raw: Optional[str], field: str = "value") -> Optional[float]:
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid numeric value for {field}: {raw!r}")

    def _to_int(raw: Optional[str], field: str = "value") -> Optional[int]:
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid integer value for {field}: {raw!r}")

    price = _to_float(_get("price_amount"), "price_amount")
    year = _to_int(_get("year"), "year")
    mileage = _to_int(_get("mileage_km"), "mileage_km")
    power = _to_float(_get("power_kw"), "power_kw")
    disp = _to_int(_get("engine_displacement_cc"), "engine_displacement_cc")
    owners = _to_int(_get("previous_owner_count"), "previous_owner_count")

    url = _get("url")
    brand = _get("brand")

    if not url and not brand:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'url' or 'brand' must be provided.",
        )

    listing = VehicleListing(
        source_marketplace=payload.get("portal"),
        url=url,
        brand=brand,
        model=_get("model"),
        year=year,
        first_registration=_get("first_registration"),
        mileage_km=mileage,
        previous_owner_count=owners,
        price_amount=price,
        price_currency=_get("price_currency") or "EUR",
        engine_displacement_cc=disp,
        power_kw=power,
        fuel_type=_get("fuel_type"),
        transmission=_get("transmission"),
        color=_get("color"),
        vehicle_category=_get("vehicle_category"),
        vehicle_type=_get("vehicle_type"),
        location_city=_get("location_city"),
        condition=_get("condition"),
        source_image_hash=image_hash,
        source_image_path=filename,
    )

    try:
        row_id, action = upsert_listing(listing)
    except Exception as exc:
        ops_logger.log_error("save", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    ops_logger.log_save(row_id, listing.url,
                        generate_fingerprint(listing.brand, listing.model,
                                             listing.year, listing.mileage_km,
                                             listing.price_amount),
                        action, price)

    return {"id": row_id, "action": action}


@application.get("/api/listings")
def list_listings(
    source: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    km_min: Optional[int] = None,
    km_max: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> list[dict[str, Any]]:
    return query_listings(
        source=source, brand=brand, model=model,
        year_min=year_min, year_max=year_max,
        km_min=km_min, km_max=km_max,
        price_min=price_min, price_max=price_max,
    )


@application.get("/api/listings/{listing_id}/price_history")
def price_history(listing_id: int) -> list[dict[str, Any]]:
    return get_price_history(listing_id)


@application.get("/api/logs")
def get_logs() -> list[dict[str, Any]]:
    return ops_logger.export_logs()


@application.get("/api/logs/export")
def export_logs_json() -> JSONResponse:
    logs = ops_logger.export_logs()
    return JSONResponse(
        content=logs,
        headers={"Content-Disposition": "attachment; filename=ucm_logs.json"},
    )
