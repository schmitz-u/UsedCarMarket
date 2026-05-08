from __future__ import annotations

import hashlib
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import app.logger as ops_logger
from app.db import (
    check_existing,
    clear_db,
    get_listing,
    get_price_history,
    init_db,
    query_listings,
    update_listing_fields,
    upsert_listing,
)
from app.extractors import detect_and_extract
from app.models import VehicleListing
from app.normalizers import (
    generate_fingerprint,
    harmonize_listing_title,
    infer_engine_displacement_cc,
    normalize_seller_type,
    validate_harmonized_listing,
    HarmonizationConflict,
)
from app.ocr import run_ocr_from_bytes

STATIC_DIR = Path(__file__).parent / "static"
_UPLOAD_IMAGE_CACHE: dict[str, tuple[bytes, str]] = {}


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
    content_type = file.content_type or "image/png"
    _UPLOAD_IMAGE_CACHE[image_hash] = (data, content_type)

    ocr_text = run_ocr_from_bytes(data)

    extraction = detect_and_extract(ocr_text)
    extraction.ocr_text = ocr_text

    ops_logger.log_upload(
        file.filename or "", image_hash, extraction.source_marketplace
    )
    ops_logger.log_ocr(image_hash, len(ocr_text), extraction.overall_confidence())

    listing = extraction.to_vehicle_listing()
    fingerprint = generate_fingerprint(
        listing.brand,
        listing.model,
        listing.year,
        listing.mileage_km,
        listing.price_amount,
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
            "seller_type": _fe(extraction.seller_type),
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
    image_blob: bytes | None = None
    image_mime_type: str | None = None

    if image_hash:
        cached_image = _UPLOAD_IMAGE_CACHE.get(image_hash)
        if cached_image:
            image_blob, image_mime_type = cached_image

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
            raise HTTPException(
                status_code=400, detail=f"Invalid numeric value for {field}: {raw!r}"
            )

    def _to_int(raw: Optional[str], field: str = "value") -> Optional[int]:
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid integer value for {field}: {raw!r}"
            )

    price = _to_float(_get("price_amount"), "price_amount")
    year = _to_int(_get("year"), "year")
    mileage = _to_int(_get("mileage_km"), "mileage_km")
    power = _to_float(_get("power_kw"), "power_kw")
    disp = _to_int(_get("engine_displacement_cc"), "engine_displacement_cc")
    owners = _to_int(_get("previous_owner_count"), "previous_owner_count")

    url = _get("url")
    brand = _get("brand")
    model = _get("model")
    transmission = _get("transmission")
    condition = _get("condition")

    harmonized = harmonize_listing_title(
        brand,
        model,
        transmission,
        condition,
        year,
        source_url=url,
    )

    try:
        validate_harmonized_listing(harmonized, year)
    except HarmonizationConflict as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not url and not brand:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'url' or 'brand' must be provided.",
        )

    if disp is None:
        disp = infer_engine_displacement_cc(
            harmonized["model_variant_normalized"], year
        )

    canonical_variant = harmonized["model_variant_normalized"]
    canonical_series = harmonized.get("series_identifier")
    canonical_model = model
    if canonical_variant:
        canonical_model = (
            f"{canonical_variant} {canonical_series}"
            if canonical_series
            else canonical_variant
        )
    if not canonical_model:
        canonical_model = harmonized["model_family_normalized"]

    listing = VehicleListing(
        source_marketplace=payload.get("portal"),
        url=url,
        brand=brand,
        model=canonical_model,
        brand_normalized=harmonized["brand_normalized"],
        model_family_normalized=harmonized["model_family_normalized"],
        model_variant_normalized=harmonized["model_variant_normalized"],
        trim_normalized=harmonized["trim_normalized"],
        drivetrain_or_gearbox_normalized=harmonized["drivetrain_or_gearbox_normalized"],
        marketing_tags_json=harmonized["marketing_tags_json"],
        ownership_hint=harmonized["ownership_hint"],
        seller_normalized=_get("seller_type") or harmonized["seller_normalized"],
        title_raw=harmonized["title_raw"],
        title_harmonized=harmonized["title_harmonized"],
        year=year,
        first_registration=_get("first_registration"),
        mileage_km=mileage,
        previous_owner_count=owners,
        price_amount=price,
        price_currency=_get("price_currency") or "EUR",
        engine_displacement_cc=disp,
        power_kw=power,
        fuel_type=_get("fuel_type"),
        transmission=transmission,
        color=_get("color"),
        vehicle_category=_get("vehicle_category"),
        vehicle_type=_get("vehicle_type"),
        location_city=_get("location_city"),
        condition=condition,
        source_image_hash=image_hash,
        source_image_mime_type=image_mime_type,
        source_image_bytes=image_blob,
        source_image_path=filename,
    )

    try:
        row_id, action = upsert_listing(listing)
    except Exception as exc:
        ops_logger.log_error("save", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    ops_logger.log_save(
        row_id,
        listing.url,
        generate_fingerprint(
            listing.brand,
            listing.model,
            listing.year,
            listing.mileage_km,
            listing.price_amount,
        ),
        action,
        price,
    )

    if image_hash:
        _UPLOAD_IMAGE_CACHE.pop(image_hash, None)

    return {"id": row_id, "action": action}


@application.delete("/api/clear-db")
def clear_all_listings() -> dict[str, str]:
    """Delete all listings and price history, reset autoincrement counters."""
    clear_db()
    return {"status": "cleared"}


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
    rows = query_listings(
        source=source,
        brand=brand,
        model=model,
        year_min=year_min,
        year_max=year_max,
        km_min=km_min,
        km_max=km_max,
        price_min=price_min,
        price_max=price_max,
    )
    for row in rows:
        has_image = bool(row.get("has_image"))
        row["has_image"] = has_image
        row["image_url"] = f"/api/listings/{row['id']}/image" if has_image else None
    return rows


@application.get("/api/listings/{listing_id}/price_history")
def price_history(listing_id: int) -> list[dict[str, Any]]:
    return get_price_history(listing_id)


@application.get("/api/listings/{listing_id}/image")
def listing_image(listing_id: int) -> Response:
    listing = get_listing(listing_id)
    if not listing or listing.get("source_image_blob") is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(
        content=listing["source_image_blob"],
        media_type=listing.get("source_image_mime_type") or "image/png",
    )


@application.put("/api/listings/{listing_id}")
def update_listing(listing_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    existing = get_listing(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing not found")

    def _clean_text(v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    def _to_int(v: Any, field: str) -> Optional[int]:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid integer for {field}")

    def _to_float(v: Any, field: str) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid number for {field}")

    updates: dict[str, Any] = {}
    if "source_marketplace" in payload:
        updates["source_marketplace"] = _clean_text(payload.get("source_marketplace"))
    if "url" in payload:
        updates["url"] = _clean_text(payload.get("url"))
    if "brand" in payload:
        updates["brand"] = _clean_text(payload.get("brand"))
    if "model" in payload:
        updates["model"] = _clean_text(payload.get("model"))
    if "year" in payload:
        updates["year"] = _to_int(payload.get("year"), "year")
    if "mileage_km" in payload:
        updates["mileage_km"] = _to_int(payload.get("mileage_km"), "mileage_km")
    if "price_amount" in payload:
        updates["price_amount"] = _to_float(payload.get("price_amount"), "price_amount")
    if "price_currency" in payload:
        updates["price_currency"] = _clean_text(payload.get("price_currency")) or "EUR"
    if "fuel_type" in payload:
        updates["fuel_type"] = _clean_text(payload.get("fuel_type"))
    if "transmission" in payload:
        updates["transmission"] = _clean_text(payload.get("transmission"))
    if "color" in payload:
        updates["color"] = _clean_text(payload.get("color"))
    if "location_city" in payload:
        updates["location_city"] = _clean_text(payload.get("location_city"))
    if "engine_displacement_cc" in payload:
        updates["engine_displacement_cc"] = _to_int(
            payload.get("engine_displacement_cc"), "engine_displacement_cc"
        )
    if "trim_normalized" in payload:
        updates["trim_normalized"] = _clean_text(payload.get("trim_normalized"))
    if "seller_normalized" in payload:
        seller = _clean_text(payload.get("seller_normalized"))
        if seller and seller not in ("Händler", "Privat"):
            raise HTTPException(
                status_code=400, detail="Seller must be Händler or Privat"
            )
        updates["seller_normalized"] = seller
        updates["condition"] = seller

    merged = dict(existing)
    merged.update({k: v for k, v in updates.items() if v is not None or k in updates})

    harmonized = harmonize_listing_title(
        merged.get("brand"),
        merged.get("model"),
        merged.get("transmission"),
        merged.get("condition"),
        merged.get("year"),
        source_url=merged.get("url"),
    )
    try:
        validate_harmonized_listing(harmonized, merged.get("year"))
    except HarmonizationConflict as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    updates["brand_normalized"] = harmonized["brand_normalized"]
    updates["model_family_normalized"] = harmonized["model_family_normalized"]
    updates["model_variant_normalized"] = harmonized["model_variant_normalized"]
    updates["drivetrain_or_gearbox_normalized"] = harmonized[
        "drivetrain_or_gearbox_normalized"
    ]
    if "trim_normalized" not in updates:
        updates["trim_normalized"] = harmonized["trim_normalized"]
    updates["marketing_tags_json"] = harmonized["marketing_tags_json"]
    updates["ownership_hint"] = harmonized["ownership_hint"]
    if "engine_displacement_cc" not in updates:
        updates["engine_displacement_cc"] = infer_engine_displacement_cc(
            harmonized["model_variant_normalized"], merged.get("year")
        )
    if "seller_normalized" not in updates:
        updates["seller_normalized"] = harmonized[
            "seller_normalized"
        ] or normalize_seller_type(merged.get("condition"))
    updates["title_raw"] = harmonized["title_raw"]
    updates["title_harmonized"] = harmonized["title_harmonized"]

    fp = generate_fingerprint(
        merged.get("brand"),
        merged.get("model"),
        merged.get("year"),
        merged.get("mileage_km"),
        merged.get("price_amount"),
    )
    updates["listing_fingerprint"] = fp

    row = update_listing_fields(listing_id, updates, source_event_type="manual_edit")
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"id": listing_id, "action": "updated"}


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
