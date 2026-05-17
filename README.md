# Used Vehicle Market Analyzer

A browser extension (MV3, Edge/Chrome) that extracts vehicle listing data from used-vehicle market portals, stores it locally via IndexedDB, and provides a visual price-analysis side panel.

## Supported portals
| Portal | Match pattern | Extraction |
|---|---|---|
| mobile.de | `*.mobile.de/fahrzeuge/details*` | `data-testid` attributes |
| AutoScout24 | `*.autoscout24.de/angebote/*` | JSON-LD (`application/ld+json`) |

## Prerequisites
- Node.js 20+
- npm 9+

## Setup
```bash
cd extension
npm install
```

## Build
```bash
npm run build
# Output: extension/dist/
```

## Test
```bash
npm test
```

## Load in Edge (or Chrome)
1. Run `npm run build`
2. Open `edge://extensions` (or `chrome://extensions`)
3. Enable **Developer mode**
4. Click **Load unpacked** → select the `extension/dist/` folder

## Architecture
```
extension/
  src/
    types/        # Canonical VehicleListing + message types
    db/           # IndexedDB persistence (upsert + price history)
    parsers/      # Parser interface, registry, mobile.de + AutoScout24 parsers
    background/   # MV3 service worker — message broker + side panel opener
    content/      # Content script — status badge injected into listing pages
    sidepanel/    # Side panel UI — Chart.js scatter plot, filters, listing cards
  tests/
    parsers/      # Vitest parser unit tests
    fixtures/     # Saved HTML pages used as test fixtures (never live requests)
```

## Key design decisions
- **No live requests during tests** — only saved HTML fixtures under `tests/fixtures/`
- **IndexedDB** for persistence (no native messaging host required for MVP)
- **Vanilla TypeScript + HTML** — no framework overhead in the side panel
- **price_amount** on `vehicle_listings` is the latest known price; full history in `listing_price_history`
