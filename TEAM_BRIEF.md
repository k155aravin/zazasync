# ZazaSync Team Brief

## One-line idea

ZazaSync is a Quebec SQDC product intelligence platform that helps adults 21+ find products, check store availability evidence, track new drops, and set alerts when products come back in stock.

## What we are building

ZazaSync should feel like a cleaner, more product-focused cousin of WeedCrawler:

- WeedCrawler is strongest as a store inventory browser.
- ZazaSync should become a product discovery and availability platform.
- The user should be able to search a product first, then answer: where can I get it, is it fresh, is it in stock, and should I set an alert?

ZazaSync does not sell cannabis. It shows SQDC product intelligence, inventory evidence, and market signals.

## What exists today

The live site already has useful structure:

- Home page with product count, snapshot freshness, age gate, and platform disclaimer
- Inventory page with search, filters, categories, brands, prices, formats, availability, images, THC/CBD, and store row evidence
- Store coverage page with tracked SQDC locations and availability-row counts
- New drops, radar picks, brands, categories, and data status sections
- Public disclaimer that ZazaSync is independent and does not sell cannabis

Current live snapshot observed June 1, 2026:

- 289 products tracked
- 106 stores tracked
- 80% availability rate shown on the homepage
- Snapshot checked June 1 around 6:56 p.m.

## Product positioning

The clearest positioning:

> Find the SQDC product you want, see where it appears available, and get notified when it comes back.

Do not position ZazaSync as a developer API or internal sync terminal. Keep it customer-facing:

- Product discovery
- Store availability
- New drops
- Radar picks
- Alerts
- Market intelligence

## Core user flow

1. User searches for a product, brand, category, format, or potency.
2. ZazaSync shows product cards with price, THC/CBD, category, brand, image status, and availability evidence.
3. User opens a product detail page.
4. Product page shows:
   - Price
   - Format
   - THC/CBD
   - Brand
   - Category
   - Stores with stock evidence
   - Last checked time
   - Related products
5. If the product is unavailable, user taps `Alert me`.
6. User chooses email, SMS, or both.
7. ZazaSync notifies them when the product appears available again.

## Main sections

### 1. Inventory

Purpose: browse and search all tracked SQDC products.

Must have:

- Search
- Category filters
- Brand filters
- Availability filters
- Price filters
- Format filters
- THC/CBD captured filter
- Image available filter
- Store row evidence filter

### 2. Product Detail

Purpose: one product, all useful information.

Must have:

- Product name
- Brand
- Category
- Format
- Price
- THC/CBD
- Product image when available
- Store availability evidence
- Last checked time
- `Alert me` action

### 3. Stores

Purpose: show where ZazaSync has availability evidence.

Must have:

- Store name
- City
- Number of rows captured
- Number of available products
- Last checked date/time
- Filter to stores with available products

### 4. New Drops

Purpose: show what is newly detected.

Must have:

- New products by date
- Category
- Brand
- Price
- Image/potency status
- Store availability evidence

### 5. Radar Picks

Purpose: curated or algorithmic highlights.

Must have:

- Trending products
- Recently restocked products
- Products with strong availability changes
- Interesting price/value picks

### 6. Alerts

Purpose: get users to create accounts and return.

Must have:

- Alert me when back in stock
- Alert me when price drops
- Alert me when available near my preferred store
- Email alerts first
- SMS alerts later

## Account/profile concept

The profile should be useful for the user first.

User-facing profile:

- Saved products
- Product alerts
- Preferred stores
- Preferred categories
- Email/SMS preferences
- Age gate confirmation

Business/analytics side:

- Use anonymized and aggregated data only
- Track demand by age range, region, category, brand, and format
- Do not sell identifiable user data

Example safe insight:

> Montreal users age 25-34 are setting more alerts for high-THC pre-rolls this week.

## MVP priorities

### Phase 1: Make the current web product clear

- Improve homepage messaging
- Make Inventory the primary call to action
- Add product detail pages if not already complete
- Add visible `Alert me` buttons for unavailable products
- Add a simple email capture flow for alerts

### Phase 2: Accounts and alerts

- User signup/login
- Saved products
- Preferred stores
- Email notification service
- Alert history

### Phase 3: Better intelligence

- New drop detection
- Restock detection
- Price change detection
- Trending products
- Store freshness score

### Phase 4: Business dashboard

- Aggregated demand reports
- Category trends
- Brand demand
- Regional interest
- Price sensitivity
- Exportable reports

## What to show the team

The meeting story should be simple:

1. WeedCrawler proves people care about SQDC stock visibility.
2. ZazaSync already has a working SQDC product snapshot.
3. ZazaSync should focus on product discovery plus availability alerts.
4. The first revenue/value hook is user accounts and alerts.
5. The long-term business hook is anonymized market intelligence.

## Immediate next decisions

- Do we build alerts first, or product detail pages first?
- Do we require accounts before alerts, or allow email-only alerts?
- Do we start with email alerts only, or include SMS from day one?
- Do we want ZazaSync to be English-only first, French-first, or bilingual?
- Do we want a mobile-first web app before a native mobile app?

## Recommended direction

Build ZazaSync as a mobile-first web app first.

Do not start with a native iOS/Android app. The web app can already serve users, collect feedback, prove demand, and be shared with the team faster. Once alerts and profiles are working, then decide whether a native app is worth it.
