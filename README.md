# ZazaSync

> Find SQDC products near you, check availability, and get alerted when they come back in stock.

ZazaSync is a Quebec cannabis inventory intelligence concept for adults 21+. The product direction is inspired by WeedCrawler, but the goal is not to copy it directly. ZazaSync should be more product-first, simpler to understand, and built around search, availability, watchlists, and alerts.

## Current Direction

The clearest user promise is:

> I am looking for a product. Is it available near me? If not, alert me.

That is the main experience ZazaSync should make effortless.

## Prototype Files

| File | Purpose |
|---|---|
| [zazasync.html](./zazasync.html) | Main webmaster handoff page: search-first inventory homepage |
| [zazasync-auth.html](./zazasync-auth.html) | Account/sign-in prototype for alerts, watchlist, preferred stores, and 21+ signup |
| [zazasync-web-v2.html](./zazasync-web-v2.html) | Latest preferred visual direction: clean search-first desktop web prototype |
| [TEAM_BRIEF.md](./TEAM_BRIEF.md) | Team product brief with strategy, UX flow, MVP priorities, and next decisions |

## Preferred UX

The new web direction should feel like a focused product marketplace:

- Big search bar on the homepage
- Quick filters such as `In stock`, `New drops`, `Back in stock`, `Under $25`, `Pre-rolls`, and `CBD`
- Product cards with brand, product name, format, price, THC/CBD, and stock status
- Recently restocked products
- Email/SMS alert capture for out-of-stock products
- Stores with the most availability
- Clear 21+ and SQDC independence disclaimer

## Main User Flow

1. User lands on ZazaSync.
2. User searches by product, brand, price, potency, or category.
3. ZazaSync shows simple product cards.
4. User opens a product to see availability by SQDC store.
5. If the product is out of stock, user taps `Alert me`.
6. User chooses email, SMS, or both.
7. ZazaSync notifies the user when the product appears available again.

## Features That Make ZazaSync Different

These are simple but important features that can make ZazaSync more useful than a basic inventory browser:

- Back-in-stock alerts
- Saved product watchlist
- Preferred SQDC stores
- Price drop alerts
- Recently restocked page
- New drops by category
- Best value score based on price, format, potency, and availability
- Product comparison

## Recommended MVP

Start simple. Build the useful loop first:

1. Search and browse inventory
2. Product detail pages
3. Store availability evidence
4. Back-in-stock email alerts
5. Saved products
6. Preferred stores
7. SMS alerts after email alerts are working

## Suggested Navigation

```text
Inventory
New Drops
Back in Stock
Stores
Watchlist
```

Future sections can include:

```text
Trends
Brands
Categories
Profile
```

## Data Model Direction

The app should eventually work from real inventory records:

- `products`: name, brand, format, category, type, strain, THC/CBD, price
- `stores`: SQDC store name, city, region, latest check time
- `inventory`: product-store stock state, availability evidence, restock status
- `alerts`: user contact, product, store/region preference, notification channel
- `watchlist`: saved products and preferred stores

## Product Positioning

ZazaSync does not sell cannabis. It helps users understand public SQDC product availability.

Keep the experience customer-facing:

- Product discovery
- Store availability
- New drops
- Back-in-stock alerts
- Saved products
- Market intelligence later

Avoid positioning it as:

- A developer API
- A scraper terminal
- A technical data dashboard

## Team Notes

The strongest first demo is not a complex backend. It is a clear experience:

```text
Search product -> See availability -> If unavailable, set alert
```

That is easy for the team to understand, easy for users to value, and useful enough to justify accounts/profiles later.

## Disclaimer

ZazaSync is an independent prototype. It is not affiliated with or endorsed by SQDC, SAQ, or any government entity. Cannabis is legal for adults 21+ in Quebec. Please consume responsibly.
