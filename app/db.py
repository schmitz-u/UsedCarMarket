from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, Optional

from app.models import VehicleListing
from app.normalizers import generate_fingerprint

DB_PATH = "used_car_market.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vehicle_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_marketplace TEXT,
    listing_id TEXT,
    url TEXT UNIQUE,
    listing_fingerprint TEXT UNIQUE NOT NULL,
    vehicle_type TEXT,
    brand TEXT,
    model TEXT,
    year INTEGER,
    first_registration TEXT,
    mileage_km INTEGER,
    previous_owner_count INTEGER,
    price_amount REAL,
    price_currency TEXT,
    price_negotiable INTEGER,
    engine_displacement_cc INTEGER,
    power_kw REAL,
    fuel_type TEXT,
    transmission TEXT,
    color TEXT,
    vehicle_category TEXT,
    location_city TEXT,
    condition TEXT,
    source_image_path TEXT,
    source_image_hash TEXT,
    ocr_confidence_overall REAL,
    extraction_timestamp_utc TEXT NOT NULL,
    raw_payload_json TEXT
);

CREATE TABLE IF NOT EXISTS listing_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_listing_id INTEGER NOT NULL REFERENCES vehicle_listings(id),
    observed_price_amount REAL NOT NULL,
    observed_price_currency TEXT,
    observed_at_utc TEXT NOT NULL,
    source_event_type TEXT,
    source_image_hash TEXT
);
"""


def _db_path() -> str:
    return DB_PATH


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: str | None = None) -> None:
    """Create tables if they do not exist."""
    global DB_PATH
    if path is not None:
        DB_PATH = path
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _build_fingerprint(listing: VehicleListing) -> str:
    if listing.listing_fingerprint:
        return listing.listing_fingerprint
    return generate_fingerprint(listing.brand, listing.model, listing.year,
                                listing.mileage_km, listing.price_amount)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_listing(listing: VehicleListing,
                   source_event_type: str = "initial_capture") -> tuple[int, str]:
    """
    Insert a new listing or update an existing one.

    Dedup is attempted first by URL, then by listing_fingerprint.
    Returns (row_id, action) where action is 'inserted' or 'updated'.
    """
    fingerprint = _build_fingerprint(listing)
    now = _now_utc()

    with _connect() as conn:
        existing = None
        if listing.url:
            row = conn.execute(
                "SELECT id FROM vehicle_listings WHERE url = ?", (listing.url,)
            ).fetchone()
            if row:
                existing = row["id"]

        if existing is None:
            row = conn.execute(
                "SELECT id FROM vehicle_listings WHERE listing_fingerprint = ?",
                (fingerprint,),
            ).fetchone()
            if row:
                existing = row["id"]

        raw_json = json.dumps(
            {k: v for k, v in listing.__dict__.items() if k != "raw_payload_json"},
            ensure_ascii=False,
        )

        if existing is None:
            cur = conn.execute(
                """INSERT INTO vehicle_listings
                   (source_marketplace, listing_id, url, listing_fingerprint,
                    vehicle_type, brand, model, year, first_registration,
                    mileage_km, previous_owner_count, price_amount, price_currency,
                    price_negotiable, engine_displacement_cc, power_kw, fuel_type,
                    transmission, color, vehicle_category, location_city, condition,
                    source_image_path, source_image_hash, ocr_confidence_overall,
                    extraction_timestamp_utc, raw_payload_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    listing.source_marketplace, listing.listing_id,
                    listing.url, fingerprint,
                    listing.vehicle_type, listing.brand, listing.model,
                    listing.year, listing.first_registration,
                    listing.mileage_km, listing.previous_owner_count,
                    listing.price_amount, listing.price_currency,
                    int(listing.price_negotiable) if listing.price_negotiable is not None else None,
                    listing.engine_displacement_cc, listing.power_kw,
                    listing.fuel_type, listing.transmission, listing.color,
                    listing.vehicle_category, listing.location_city, listing.condition,
                    listing.source_image_path, listing.source_image_hash,
                    listing.ocr_confidence_overall, now, raw_json,
                ),
            )
            row_id = cur.lastrowid
            action = "inserted"
        else:
            conn.execute(
                """UPDATE vehicle_listings SET
                   source_marketplace=?, listing_id=?, url=?, listing_fingerprint=?,
                   vehicle_type=?, brand=?, model=?, year=?, first_registration=?,
                   mileage_km=?, previous_owner_count=?, price_amount=?,
                   price_currency=?, price_negotiable=?, engine_displacement_cc=?,
                   power_kw=?, fuel_type=?, transmission=?, color=?,
                   vehicle_category=?, location_city=?, condition=?,
                   source_image_path=?, source_image_hash=?, ocr_confidence_overall=?,
                   extraction_timestamp_utc=?, raw_payload_json=?
                   WHERE id=?
                """,
                (
                    listing.source_marketplace, listing.listing_id,
                    listing.url, fingerprint,
                    listing.vehicle_type, listing.brand, listing.model,
                    listing.year, listing.first_registration,
                    listing.mileage_km, listing.previous_owner_count,
                    listing.price_amount, listing.price_currency,
                    int(listing.price_negotiable) if listing.price_negotiable is not None else None,
                    listing.engine_displacement_cc, listing.power_kw,
                    listing.fuel_type, listing.transmission, listing.color,
                    listing.vehicle_category, listing.location_city, listing.condition,
                    listing.source_image_path, listing.source_image_hash,
                    listing.ocr_confidence_overall, now, raw_json,
                    existing,
                ),
            )
            row_id = existing
            action = "updated"

        if listing.price_amount is not None:
            conn.execute(
                """INSERT INTO listing_price_history
                   (vehicle_listing_id, observed_price_amount, observed_price_currency,
                    observed_at_utc, source_event_type, source_image_hash)
                   VALUES (?,?,?,?,?,?)
                """,
                (
                    row_id, listing.price_amount, listing.price_currency,
                    now, source_event_type, listing.source_image_hash,
                ),
            )

    return row_id, action


def get_listing(listing_id: int) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM vehicle_listings WHERE id=?", (listing_id,)
        ).fetchone()
        return dict(row) if row else None


def query_listings(
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
    conditions = []
    params: list[Any] = []

    if source:
        conditions.append("source_marketplace = ?")
        params.append(source)
    if brand:
        conditions.append("lower(brand) LIKE ?")
        params.append(f"%{brand.lower()}%")
    if model:
        conditions.append("lower(model) LIKE ?")
        params.append(f"%{model.lower()}%")
    if year_min is not None:
        conditions.append("year >= ?")
        params.append(year_min)
    if year_max is not None:
        conditions.append("year <= ?")
        params.append(year_max)
    if km_min is not None:
        conditions.append("mileage_km >= ?")
        params.append(km_min)
    if km_max is not None:
        conditions.append("mileage_km <= ?")
        params.append(km_max)
    if price_min is not None:
        conditions.append("price_amount >= ?")
        params.append(price_min)
    if price_max is not None:
        conditions.append("price_amount <= ?")
        params.append(price_max)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM vehicle_listings {where} ORDER BY extraction_timestamp_utc DESC"

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_price_history(listing_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM listing_price_history
               WHERE vehicle_listing_id=? ORDER BY observed_at_utc""",
            (listing_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def check_existing(url: Optional[str], fingerprint: str) -> Optional[int]:
    """Return the row id of an existing listing matching url or fingerprint, or None."""
    with _connect() as conn:
        if url:
            row = conn.execute(
                "SELECT id FROM vehicle_listings WHERE url=?", (url,)
            ).fetchone()
            if row:
                return row["id"]
        row = conn.execute(
            "SELECT id FROM vehicle_listings WHERE listing_fingerprint=?", (fingerprint,)
        ).fetchone()
        return row["id"] if row else None
