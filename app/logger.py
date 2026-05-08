from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

_log_records: list[dict[str, Any]] = []
_logger = logging.getLogger("ucm.ops")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _record(event: str, payload: dict[str, Any]) -> None:
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    _log_records.append(entry)
    _logger.info("[%s] %s", event, json.dumps(payload, ensure_ascii=False))


def log_upload(filename: str, image_hash: str, portal: str | None) -> None:
    _record("upload", {"filename": filename, "image_hash": image_hash, "portal": portal})


def log_ocr(image_hash: str, text_length: int, confidence: float) -> None:
    _record("ocr", {"image_hash": image_hash, "text_length": text_length, "confidence": confidence})


def log_save(listing_id: int | None, url: str | None, fingerprint: str,
             action: str, price: float | None) -> None:
    _record("save", {
        "listing_id": listing_id, "url": url,
        "fingerprint": fingerprint, "action": action, "price": price,
    })


def log_error(context: str, error: str) -> None:
    _record("error", {"context": context, "error": error})


def export_logs() -> list[dict[str, Any]]:
    return list(_log_records)


def clear_logs() -> None:
    _log_records.clear()
