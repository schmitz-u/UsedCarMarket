# Product Requirements Document (PRD)

## Product Name
Used Vehicle Market Analyzer Browser Extension

## Date
2026-05-03

## Author
Project Owner

## 1. Background and Goal
The product is a browser extension (primary target: Microsoft Edge, with compatibility for other major Chromium-based browsers and ideally Firefox) that helps users analyze vehicle offers on used vehicle market portals.

The extension will:
1. Extract listing characteristics from offer pages.
2. Store extracted data in a local SQLite database.
3. Provide analysis and visual pricing insights based on selected filters.

The initial focus is to define and deliver a reliable MVP data-capture pipeline before advanced analysis features.

## 2. Problem Statement
Users browsing used vehicle portals (motorcycles first, but extendable to other vehicle categories) cannot easily build a historical local dataset for objective comparison. Market decisions are often made from incomplete snapshots.

A local structured dataset plus visual analysis enables better understanding of price positioning by mileage, year, and related factors.

## 3. Objectives
1. Capture and persist normalized listing data from supported pages.
2. Support manual and/or batch capture workflows while browsing.
3. Allow filtering and visualization of stored data (for a subset or all records).
4. Show price as a function of variables such as year and kilometer range using color-based representation.
5. Provide immediate user feedback about whether the currently viewed listing is already stored.
6. Track price development over time for each listing.

## 4. Scope
### In Scope (MVP)
1. Browser extension foundation (manifest, permissions, popup/options UI).
2. Data extraction from listing pages for key fields:
   - Manufacturer/brand
   - Model
   - Year
   - Mileage (KM)
   - Previous owner count
   - Price
   - Listing URL
   - Marketplace/source
   - Timestamp of extraction
3. Explicit user action button to trigger analysis and storage of the currently visible offer.
4. Local storage to SQLite via extension-compatible architecture (for example: background service + local companion process/API if needed by browser constraints).
5. Basic analysis screen with filtering and a color-coded chart/table where price is the dependent variable.
6. Parallel workflow where the offer page and analysis view can be open side-by-side.
7. Immediate update of analysis information after new storage action, with visual indication of newly added entry.

### Out of Scope (Initial MVP)
1. Full cross-marketplace scraping engine with anti-bot bypass.
2. Cloud sync, multi-user features, or remote DB hosting.
3. Automated valuation recommendations.
4. Native mobile browser support.

## 5. Target Users
1. Private buyers comparing used motorcycles and vehicles.
2. Enthusiasts tracking market trends for selected models.
3. Small resellers needing lightweight local market monitoring.

## 6. Functional Requirements
### FR-1: Listing Data Capture
1. The extension shall detect supported listing pages.
2. The extension shall extract configured fields from the page DOM.
3. The extension shall provide a dedicated button that triggers analysis and storage of the current listing.
4. The extension shall prevent duplicate records based on URL and/or marketplace listing ID.
5. The extension shall show whether the currently visible listing is already present in the database.

### FR-2: Data Storage
1. Captured data shall be persisted to SQLite.
2. The data model shall support motorcycles first and be extensible for other vehicle types.
3. The system shall store extraction timestamp and source metadata.
4. The system shall store price history so that multiple price values over time can exist for the same listing.

### FR-3: Data Quality and Validation
1. Numeric fields (price, KM, year, owner count) shall be normalized to numeric types.
2. Missing fields shall be stored as null and flagged in metadata.
3. Parsing errors shall be logged with listing URL for troubleshooting.

### FR-4: Filtering and Analysis
1. User shall be able to filter by manufacturer, model, year range, KM range, price range, and source.
2. User shall be able to select all records or a filtered subset.
3. System shall render a visual representation where price is color-coded against variables such as year and KM.
4. After a new listing is stored, the analysis view shall refresh and include the new entry.
5. Newly added entries shall be visually indicated in the analysis information.

### FR-5: UX and Controls
1. Popup or side panel shall expose capture controls and quick status.
2. Analysis view shall allow adjusting filters and refreshing results.
3. User shall be able to open the original listing URL from stored records.
4. UI shall clearly indicate if the currently viewed offer is already stored in the database.
5. User shall be able to keep offer page and analysis view visible in parallel (for example via side panel, split view, or separate window).

## 7. Non-Functional Requirements
1. Browser support:
   - Primary: Microsoft Edge.
   - Secondary: Chromium-compatible browsers.
   - Stretch target: Firefox.
2. Performance:
   - Capture action should complete within 2 seconds for typical listing pages.
3. Reliability:
   - No data loss on browser restart for already persisted records.
4. Security and privacy:
   - Store data locally by default.
   - Request minimum required permissions.
5. Maintainability:
   - Parser logic per marketplace should be modular.

## 8. Proposed Technical Architecture (Initial)
1. Extension UI layer:
   - Popup/side panel for capture + analysis controls.
   - In-page or popup button state for "stored / not stored" indication.
2. Content scripts:
   - Marketplace-specific parsers for DOM extraction.
3. Background service worker:
   - Orchestration, validation, dedup checks, and post-save analysis refresh event.
4. Persistence layer:
   - SQLite database access through a local bridge process/API if direct browser access is restricted.

## 9. Data Model (Initial Draft)
Table: vehicle_listings
1.  id (PK)
2.  source_marketplace (text)             # e.g. mobile.de, autoscout24.de
3.  listing_id (text, nullable)            # portal-native ID (integer or UUID depending on portal)
4.  url (text, unique)
5.  vehicle_type (text)                    # motorcycle, car, etc.
6.  brand (text)
7.  model (text)
8.  year (integer, nullable)               # first registration year
9.  first_registration (text, nullable)    # MM/YYYY as shown on portal
10. mileage_km (integer, nullable)
11. previous_owner_count (integer, nullable)
12. price_amount (real, nullable)          # latest known price (convenience field)
13. price_currency (text, nullable)
14. price_negotiable (integer, nullable)   # 0/1 boolean flag
15. engine_displacement_cc (integer, nullable)
16. power_kw (real, nullable)
17. fuel_type (text, nullable)
18. transmission (text, nullable)
19. color (text, nullable)
20. vehicle_category (text, nullable)      # e.g. Tourer, Naked, Sport
21. location_city (text, nullable)
22. condition (text, nullable)             # e.g. Gebrauchtfahrzeug, Vorführfahrzeug
23. extraction_timestamp_utc (text)
24. raw_payload_json (text, nullable)      # full extracted payload for reprocessing

Table: listing_price_history
1. id (PK)
2. vehicle_listing_id (FK -> vehicle_listings.id)
3. observed_price_amount (real)
4. observed_price_currency (text, nullable)
5. observed_at_utc (text)
6. source_event_type (text, nullable)      # e.g. initial_capture, recapture

Data model notes:
1. `vehicle_listings.price_amount` may represent the latest known price for convenience.
2. `listing_price_history` is the authoritative timeline for historical price analysis.
3. `listing_id` format differs per portal: integer on mobile.de, UUID on AutoScout24.
4. `raw_payload_json` enables re-extraction of new fields without re-scraping the live page.

## 10. Supported Portals & Parser Strategy

### Overview
Each marketplace requires its own parser module. Parsers share a common output interface (the canonical vehicle_listing object) and are selected by matching the current tab URL against a known domain pattern.

### Supported Portals (Initial)

#### Portal 1: mobile.de
- **Domain pattern:** `*.mobile.de/fahrzeuge/details*`
- **Primary extraction strategy:** `data-testid` attributes in the HTML DOM.
  - These are React semantic markers, stable across visual redesigns.
- **Key selectors:**

| Field | Selector |
|---|---|
| Price (gross) | `[data-testid="vip-price-label"]` inner text |
| Mileage | `[data-testid="mileage-item"] dd.nuAmT` |
| First registration | `[data-testid="firstRegistration-item"] dd` |
| Previous owners | `[data-testid="numberOfPreviousOwners-item"] dd` |
| Engine displacement | `[data-testid="cubicCapacity-item"] dd` |
| Power | `[data-testid="power-item"] dd` |
| Fuel type | `[data-testid="fuel-item"] dd` |
| Transmission | `[data-testid="transmission-item"] dd` |
| Color | `[data-testid="color-item"] dd` |
| Condition | `[data-testid="damageCondition-item"] dd` |
| Category | `[data-testid="category-item"] dd` |
| Listing ID | URL query parameter `id` |

- **Fallback:** `og:title` and `og:description` meta tags for brand/model/year/km summary.
- **No JSON-LD** detected in current page snapshot.

#### Portal 2: AutoScout24
- **Domain pattern:** `*.autoscout24.de/angebote/*`
- **Primary extraction strategy:** `<script type="application/ld+json">` (schema.org JSON-LD).
  - Contains a fully typed `Motorbike` object with all key fields.
  - Independent of CSS class changes (CSS modules use obfuscated names like `PriceInfo_price__XU0aF`).
- **Key JSON-LD paths:**

| Field | JSON-LD path |
|---|---|
| Price | `offers.price` |
| Currency | `offers.priceCurrency` |
| Mileage (km) | `mileageFromOdometer.value` |
| First registration | `productionDate` (ISO format `YYYY-MM-DD`) |
| Previous owners | `numberOfPreviousOwners` |
| Brand | `manufacturer` |
| Model | `model` |
| Engine displacement | `vehicleEngine.engineDisplacement.value` |
| Power (kW) | `vehicleEngine.enginePower[unitCode=KWT].value` |
| Transmission | `vehicleTransmission` |
| Color | `color` |
| Body type | `bodyType` |
| Condition | `itemCondition` |
| Euro norm | `hasEnergyEfficiencyCategory` |
| Listing UUID | extracted from canonical URL path segment |

- **Fallback:** `og:title`, `og:description`, and `data-testid="price-section"` for price cross-check.

### Parser Module Interface (Canonical Output)
All parsers must map extracted data to the same canonical object before DB storage:
```json
{
  "source_marketplace": "string",
  "listing_id": "string",
  "url": "string",
  "vehicle_type": "string",
  "brand": "string",
  "model": "string",
  "first_registration": "string",
  "year": "number",
  "mileage_km": "number",
  "previous_owner_count": "number",
  "price_amount": "number",
  "price_currency": "string",
  "price_negotiable": "boolean",
  "engine_displacement_cc": "number",
  "power_kw": "number",
  "fuel_type": "string",
  "transmission": "string",
  "color": "string",
  "vehicle_category": "string",
  "location_city": "string",
  "condition": "string"
}
```
Missing fields are set to `null`. Parsers must not throw on missing fields — they log a warning and continue.

### Adding Future Portals
1. Add a new domain pattern to the manifest `content_scripts` matches.
2. Implement the parser module implementing the canonical interface above.
3. Register the parser in the portal registry (URL pattern → parser mapping).

## 11. MVP Milestones
1. Milestone 1: Extension skeleton + one marketplace parser + local save flow.
2. Milestone 2: SQLite schema + dedup + error logging.
3. Milestone 3: Basic filter UI + first color-coded price analysis view.
4. Milestone 4: Hardening, browser compatibility checks, and docs.

## 12. Risks and Mitigations
1. Marketplace DOM changes break parsers.
   - Mitigation: parser abstraction and selector versioning.
2. Browser restrictions for local SQLite access.
   - Mitigation: local companion service with minimal API.
3. Data inconsistency across marketplaces.
   - Mitigation: canonical normalization pipeline and source-specific mapping.

## 13. Success Metrics
1. Capture success rate for supported pages >= 95%.
2. Duplicate insertion rate <= 1%.
3. Filtered analysis response time <= 1 second for up to 10,000 records.
4. User can compare price trends by year/KM on stored dataset without leaving the browser workflow.

## 14. Open Questions
1. Should capture be purely manual, semi-automatic, or fully automatic while browsing?
2. Is SQLite required inside the extension package, or is a local companion app acceptable?
3. Which chart type is preferred for the first analysis screen (heatmap, scatter, or matrix table)?
