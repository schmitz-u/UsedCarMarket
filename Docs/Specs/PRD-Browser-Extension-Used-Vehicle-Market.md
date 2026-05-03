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
3. Local storage to SQLite via extension-compatible architecture (for example: background service + local companion process/API if needed by browser constraints).
4. Basic analysis screen with filtering and a color-coded chart/table where price is the dependent variable.

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
3. The extension shall allow user-triggered save of current listing.
4. The extension shall prevent duplicate records based on URL and/or marketplace listing ID.

### FR-2: Data Storage
1. Captured data shall be persisted to SQLite.
2. The data model shall support motorcycles first and be extensible for other vehicle types.
3. The system shall store extraction timestamp and source metadata.

### FR-3: Data Quality and Validation
1. Numeric fields (price, KM, year, owner count) shall be normalized to numeric types.
2. Missing fields shall be stored as null and flagged in metadata.
3. Parsing errors shall be logged with listing URL for troubleshooting.

### FR-4: Filtering and Analysis
1. User shall be able to filter by manufacturer, model, year range, KM range, price range, and source.
2. User shall be able to select all records or a filtered subset.
3. System shall render a visual representation where price is color-coded against variables such as year and KM.

### FR-5: UX and Controls
1. Popup or side panel shall expose capture controls and quick status.
2. Analysis view shall allow adjusting filters and refreshing results.
3. User shall be able to open the original listing URL from stored records.

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
2. Content scripts:
   - Marketplace-specific parsers for DOM extraction.
3. Background service worker:
   - Orchestration, validation, dedup checks.
4. Persistence layer:
   - SQLite database access through a local bridge process/API if direct browser access is restricted.

## 9. Data Model (Initial Draft)
Table: vehicle_listings
1. id (PK)
2. source_marketplace (text)
3. listing_id (text, nullable)
4. url (text, unique)
5. vehicle_type (text)
6. brand (text)
7. model (text)
8. year (integer, nullable)
9. mileage_km (integer, nullable)
10. previous_owner_count (integer, nullable)
11. price_amount (real, nullable)
12. price_currency (text, nullable)
13. extraction_timestamp_utc (text)
14. raw_payload_json (text, nullable)

## 10. MVP Milestones
1. Milestone 1: Extension skeleton + one marketplace parser + local save flow.
2. Milestone 2: SQLite schema + dedup + error logging.
3. Milestone 3: Basic filter UI + first color-coded price analysis view.
4. Milestone 4: Hardening, browser compatibility checks, and docs.

## 11. Risks and Mitigations
1. Marketplace DOM changes break parsers.
   - Mitigation: parser abstraction and selector versioning.
2. Browser restrictions for local SQLite access.
   - Mitigation: local companion service with minimal API.
3. Data inconsistency across marketplaces.
   - Mitigation: canonical normalization pipeline and source-specific mapping.

## 12. Success Metrics
1. Capture success rate for supported pages >= 95%.
2. Duplicate insertion rate <= 1%.
3. Filtered analysis response time <= 1 second for up to 10,000 records.
4. User can compare price trends by year/KM on stored dataset without leaving the browser workflow.

## 13. Open Questions
1. Which specific marketplace(s) should be supported first?
2. Should capture be purely manual, semi-automatic, or fully automatic while browsing?
3. Is SQLite required inside the extension package, or is a local companion app acceptable?
4. Which chart type is preferred for the first analysis screen (heatmap, scatter, or matrix table)?
