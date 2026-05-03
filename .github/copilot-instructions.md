# UsedCarMarket — Project Guidelines

## ⚠️ CRITICAL — NEVER interact with live portals during development
**Do NOT make any HTTP requests, fetch calls, or automated browser interactions targeting `mobile.de`, `autoscout24.de`, or any other vehicle marketplace portal.**
- Automated traffic to these portals will trigger bot detection.
- This can result in permanent account bans for the project owner.
- For parsing development and tests, use only the saved HTML examples under `Input/Examples/`.
- For integration tests, use local mock servers or static fixtures — never the live sites.

This rule applies at all times: development, testing, debugging, and code generation.

---

## What This Project Is
A browser extension (primary: Microsoft Edge, secondary: other Chromium browsers, stretch: Firefox) that extracts vehicle listing data from used-vehicle market portals, stores it in a local SQLite database, and provides a visual price analysis view.

See the full PRD: `Docs/Specs/PRD-Browser-Extension-Used-Vehicle-Market.md`

## Architecture
- **Extension UI layer**: popup or side panel — capture trigger button + analysis view
- **Content scripts**: marketplace-specific parser modules, one per portal
- **Background service worker**: orchestration, dedup, validation, post-save events
- **Persistence layer**: SQLite via a local companion service/native messaging host (direct SQLite access is not available inside the browser extension sandbox)

## Supported Portals (Initial)
| Portal | Domain pattern | Extraction strategy |
|---|---|---|
| mobile.de | `*.mobile.de/fahrzeuge/details*` | `data-testid` attributes in HTML DOM |
| AutoScout24 | `*.autoscout24.de/angebote/*` | `<script type="application/ld+json">` (schema.org JSON-LD) |

## Parser Conventions
- Every parser must output the **canonical vehicle listing object** (defined in PRD section 10).
- Parsers must **never throw** on missing fields — set missing values to `null` and log a warning with the listing URL.
- Parser modules are selected by matching the current tab URL against a domain pattern registry.
- CSS class names on both portals are obfuscated/minified — prefer `data-testid` attributes (mobile.de) or JSON-LD (AutoScout24) over class-based selectors.

## Data Model Key Points
- Two SQLite tables: `vehicle_listings` (one row per listing URL) and `listing_price_history` (time-series prices per listing).
- `price_amount` on `vehicle_listings` is a convenience field for the latest known price; `listing_price_history` is authoritative for historical analysis.
- `listing_id` format differs per portal: integer on mobile.de, UUID on AutoScout24.
- `raw_payload_json` stores the full extracted payload for reprocessing without re-scraping.

## Key UX Behaviours
- A dedicated **"Save to DB"** button triggers extraction + storage of the current listing.
- The UI must show whether the **currently viewed listing is already in the DB** (stored/not-stored state).
- After a save, the **analysis view refreshes** and the new entry is **visually highlighted**.
- The user must be able to keep the offer page and analysis view **visible in parallel** (side panel preferred).

## Coding Conventions
- Use **TypeScript** for all extension source files.
- Manifest V3 (`manifest.json`) — required for Edge/Chrome compatibility.
- Keep manifest `permissions` to the minimum required.
- Do not add comments or docstrings to code that was not modified in the current task.
- Do not add error handling for scenarios that cannot happen.

## Build & Test
_To be defined in Milestone 1. Update this section when the toolchain is established._
