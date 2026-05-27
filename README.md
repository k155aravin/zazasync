# ZazaSync

> Quebec cannabis. Synchronized.

ZazaSync is a mobile-first cannabis inventory intelligence concept for Quebec SQDC shoppers. The goal is similar to Weedcrawler: track store stock, product freshness, best sellers, restocks, and availability signals across Quebec locations, then present that data in a fast app-like experience.

## Current Prototype

| Version | File |
|---|---|
| Desktop concept | [zazasync-desktop-v1.html](./zazasync-desktop-v1.html) |
| Mobile app prototype | [zazasync-mobile-v1.html](./zazasync-mobile-v1.html) |

## Mobile App Direction

The mobile prototype is built with local mock data shaped like future live inventory records. It currently includes:

- Home dashboard with sync status, Quebec coverage stats, nearby stores, and restocked products
- Browse screen with search, category chips, type filters, sorting, and product detail sheets
- Store radar with mock map pins, stock freshness, category counts, and inventory totals
- Best-seller screen with 7, 30, and 90 day ranking windows
- Alerts/watchlist screen for restocks, low stock, and saved products
- Profile/data screen showing the live inventory entities the app expects later

## Planned Data Model

The mock frontend is ready to swap in real data from:

- `products`: name, brand, format, category, type, strain, THC/CBD, price
- `stores`: city, SQDC location name, opened date, latest sync time, category count
- `inventory`: product-store stock state, low stock flag, restock age, availability
- `rankings`: best sellers by category and time window
- `alerts`: saved products, preferred stores, restock and price-drop triggers

## Planned Platform

- SQDC product and store inventory sync
- Normalized product/store/inventory database
- Price and restock history
- Push notifications
- Store map with real coordinates

## Disclaimer

ZazaSync is an independent prototype. It is not affiliated with or endorsed by SQDC, SAQ, or any government entity. Cannabis is legal for adults 21+ in Quebec. Please consume responsibly.
