# Used Vehicle Market Analyzer — MVP

A standalone local application for analysing used-vehicle listings.
Screenshots of listing pages are uploaded manually; the app extracts fields
via OCR, lets the user review and correct the data, then persists it in a
local SQLite database for price-history tracking and visual analysis.

## ⚠️ Critical Constraint

**Never interact with live portals** (mobile.de, autoscout24.de, etc.) during
development or testing.  All input must come from locally uploaded screenshots
or fixtures under `Input/Examples/Screenshots/`.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Tesseract OCR | 5.x |

### Install Tesseract

**Ubuntu / Debian**
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-deu
```

**macOS (Homebrew)**
```bash
brew install tesseract tesseract-lang
```

**Windows**  
Download the installer from <https://github.com/UB-Mannheim/tesseract/wiki>.

---

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
# From the repository root
uvicorn app.main:application --reload --host 127.0.0.1 --port 8000
```

Open your browser at **http://127.0.0.1:8000**.

The SQLite database file (`used_car_market.db`) is created automatically in the
working directory on first run.  Override the path with the `UCM_DB_PATH`
environment variable:

```bash
UCM_DB_PATH=/data/ucm.db uvicorn app.main:application --reload
```

---

## Usage Workflow

1. **Upload & Review tab** — drag-and-drop or choose a PNG/JPG screenshot.
2. The app runs OCR, detects the portal (mobile.de or AutoScout24), and
   populates the review form with extracted values colour-coded by confidence.
3. Correct any low-confidence or missing fields, then click **Save to Database**.
4. **Analysis tab** — apply filters (brand, model, year/KM/price ranges) and
   explore the scatter chart (x=year, y=mileage, colour=price).  A newly saved
   entry is visually highlighted with a star marker.
5. **Logs tab** — view all operation events and export them as JSON for
   troubleshooting.

---

## Running Tests

```bash
# From the repository root
pytest tests/ -v
```

Test files:

| File | What it tests |
|---|---|
| `tests/test_normalizers.py` | Price, mileage, date, fingerprint normalizers |
| `tests/test_extractors.py` | Portal-specific field extraction rules |
| `tests/test_db.py` | SQLite upsert, dedup, price history, queries |
| `tests/test_integration.py` | Full API: upload → save → list → logs |

---

## Project Structure

```
app/
  main.py              FastAPI application (routes)
  models.py            Canonical vehicle listing + extraction result models
  normalizers.py       Price / mileage / date / fingerprint helpers
  ocr.py               OCR service abstraction (pytesseract)
  db.py                SQLite schema, upsert, query helpers
  logger.py            In-memory operation log + JSON export
  extractors/
    mobile_de.py       mobile.de OCR text extraction rules
    autoscout24.py     AutoScout24 OCR text extraction rules
    registry.py        Portal detection + extractor dispatch
  static/
    index.html         Single-page frontend (upload, review, analysis, logs)

tests/
  test_normalizers.py
  test_extractors.py
  test_db.py
  test_integration.py
  fixtures/            Synthetic PNG fixtures for unit/integration tests

Input/
  Examples/
    Screenshots/
      image1.png       mobile.de fixture screenshot
      image2.png       AutoScout24 fixture screenshot
```

---

## Supported Portals

| Portal | Detection | Key Fields |
|---|---|---|
| mobile.de | URL `suchen.mobile.de` or text "mobile.de" | data-testid label/value pairs in OCR |
| AutoScout24 | URL `autoscout24.de` or text "autoscout24" | Label/value pairs + title pattern |

---

## Data Model

Two SQLite tables (see `app/db.py` for full schema):

- **`vehicle_listings`** — one row per unique listing (dedup by URL, then by fingerprint).
- **`listing_price_history`** — one row per save event, enabling price tracking over time.
