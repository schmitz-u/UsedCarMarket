# Product Requirements Document (PRD)

## Product Name
Used Vehicle Market Analyzer (Standalone App)

## Date
2026-05-03

## Author
Project Owner

## ⚠️ Critical Operating Constraint
During development and testing, the system must never interact directly with live vehicle marketplaces.

1. No HTTP requests or automated browser interactions to mobile.de, autoscout24.de, or other live portals.
2. Input must come only from user-provided screenshots or local test fixtures.
3. Integration tests must run against local files/mocks only.

## 1. Background and Goal
The product is a standalone local application that helps users analyze used-vehicle offers by extracting listing details from screenshots that the user uploads manually.

The application will:
1. Accept screenshots of listing pages.
2. Extract listing characteristics via OCR + field parsing.
3. Store normalized records in local SQLite.
4. Provide filterable analysis and visual price insights.

The initial focus is to deliver a reliable ingestion and storage pipeline with review-before-save controls.

## 2. Problem Statement
Users cannot easily build a reliable local historical dataset while safely avoiding direct automation against marketplace portals. Screenshot-based ingestion provides a compliant, controlled, and auditable workflow for building price history data.

## 3. Objectives
1. Ingest listing screenshots manually.
2. Extract and normalize key vehicle fields.
3. Allow user review/correction before persistence.
4. Persist data in SQLite with price history over time.
5. Analyze filtered records with price as visual value (color).
6. Show newly saved entries immediately and highlight them in analysis.

## 4. Scope
### In Scope (MVP)
1. Standalone desktop-local app (web UI running locally is acceptable).
2. Screenshot upload workflow.
3. OCR + rule-based field extraction for initial portals (mobile.de and AutoScout24 page layouts via screenshots).
4. Review form for extracted fields before save.
5. SQLite persistence with dedup + price history.
6. Analysis view with filters and scatter plot (x=year, y=KM, color=price).
7. Immediate post-save refresh with visual highlight of the new/updated record.

### Out of Scope (Initial MVP)
1. Live portal scraping/automation.
2. Cloud sync or multi-user features.
3. Automated valuation recommendations.
4. Native mobile app.

## 5. Target Users
1. Private buyers comparing motorcycles and other vehicles.
2. Enthusiasts tracking market trends for selected models.
3. Small resellers wanting a local evidence-based comparison tool.

## 6. Functional Requirements
### FR-1: Screenshot Ingestion
1. User can upload one or more screenshots.
2. System stores source image metadata (path/name/hash/timestamp).
3. System performs OCR and attempts structured field extraction.

### FR-2: Extraction and Review
1. System extracts target fields (brand, model, year, KM, owners, price, URL, source, etc.).
2. Missing/low-confidence fields are flagged.
3. User can review and correct extracted values before saving.
4. Save is blocked only for required identifiers (URL or manual listing fingerprint).

### FR-3: Data Storage (SQLite)
1. Data is persisted to local SQLite.
2. Dedup is performed by URL when available; fallback dedup uses listing fingerprint.
3. Re-saving an existing listing updates latest values and appends a price history entry.
4. Full extracted payload is stored for future reprocessing.

### FR-4: Status and Save Feedback
1. UI indicates whether a reviewed listing appears to be already stored.
2. Save operation reports success/failure clearly.
3. New or updated entries are reflected immediately in analysis.

### FR-5: Filtering and Analysis
1. User can filter by source, brand, model, year range, KM range, and price range.
2. User can view all records or filtered subsets.
3. Scatter plot uses year on x-axis, KM on y-axis, and color for price.
4. Newly saved record is visually highlighted.

## 7. Non-Functional Requirements
1. Local-first: all data remains on local machine by default.
2. Reliability: persisted records survive app restart.
3. Performance: single screenshot extraction + parse should typically complete within 3 seconds on a standard machine.
4. Maintainability: parser/extractor rules are modular per portal layout.
5. Auditability: operations can be logged and exported for troubleshooting.

## 8. Proposed Technical Architecture (Initial)
1. UI layer:
   - Upload area, extraction review form, save controls, filters, analysis panel.
2. OCR layer:
   - Converts screenshot text into structured tokens/blocks.
3. Extraction layer:
   - Portal-specific mapping rules from OCR text to canonical object.
4. Validation/Normalization layer:
   - Numeric/date normalization, confidence flags, dedup fingerprint generation.
5. Persistence layer:
   - SQLite with repository/service access layer.
6. Analysis layer:
   - Query API for filters + chart dataset generation.

## 9. Data Model (SQLite)
Table: vehicle_listings
1. id (PK)
2. source_marketplace (text, nullable)
3. listing_id (text, nullable)
4. url (text, unique, nullable)
5. listing_fingerprint (text, unique)
6. vehicle_type (text)
7. brand (text, nullable)
8. model (text, nullable)
9. year (integer, nullable)
10. first_registration (text, nullable)
11. mileage_km (integer, nullable)
12. previous_owner_count (integer, nullable)
13. price_amount (real, nullable)
14. price_currency (text, nullable)
15. price_negotiable (integer, nullable)
16. engine_displacement_cc (integer, nullable)
17. power_kw (real, nullable)
18. fuel_type (text, nullable)
19. transmission (text, nullable)
20. color (text, nullable)
21. vehicle_category (text, nullable)
22. location_city (text, nullable)
23. condition (text, nullable)
24. source_image_path (text, nullable)
25. source_image_hash (text, nullable)
26. ocr_confidence_overall (real, nullable)
27. extraction_timestamp_utc (text)
28. raw_payload_json (text, nullable)

Table: listing_price_history
1. id (PK)
2. vehicle_listing_id (FK -> vehicle_listings.id)
3. observed_price_amount (real)
4. observed_price_currency (text, nullable)
5. observed_at_utc (text)
6. source_event_type (text, nullable) # initial_capture, recapture, manual_edit
7. source_image_hash (text, nullable)

## 10. Input Sources and Extraction Strategy
### Supported Input (MVP)
1. PNG/JPG screenshots from desktop browser pages.
2. Initial fixture set under `Input/Examples/Screenshots/`.

### Initial Portal Coverage
1. mobile.de screenshots
2. AutoScout24 screenshots

### Extraction Strategy
1. OCR pass to obtain raw text blocks.
2. Portal-specific rules detect labels and corresponding values.
3. Normalization converts locale-specific formats:
   - Price `39.990 €` -> `39990`
   - Mileage `19.600 km` -> `19600`
   - First registration `03/2026` -> month/year + numeric year.
4. Confidence scoring identifies fields requiring manual review.

## 11. MVP Milestones
1. Milestone 1: Standalone app skeleton + screenshot upload + OCR baseline.
2. Milestone 2: SQLite schema + save/review flow + dedup + price history.
3. Milestone 3: Filtering + scatter analysis + new-entry highlight.
4. Milestone 4: Hardening, logs export, and documentation.

## 12. Risks and Mitigations
1. OCR errors due to varying screenshot quality.
   - Mitigation: review-before-save UI and confidence flags.
2. Layout variation between portals and screen sizes.
   - Mitigation: rule modules per portal + fallback generic parser.
3. Missing URL in screenshot crop.
   - Mitigation: fallback fingerprint-based dedup and optional manual URL entry.

## 13. Success Metrics
1. Extraction-to-review completion rate >= 95% for screenshot fixtures.
2. Duplicate listing insertion rate <= 1%.
3. Analysis query response <= 1 second for up to 10,000 records.
4. Users can maintain price history over time without any live portal automation.

## 14. Open Questions
1. Preferred runtime stack for standalone app: Python (FastAPI/Streamlit) or Electron/Node?
2. OCR engine preference: Tesseract, EasyOCR, or external API?
3. Should batch screenshot ingestion be included in MVP or post-MVP?
