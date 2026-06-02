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
| [zazasync-onboarding.html](./zazasync-onboarding.html) | Post-signup onboarding survey for age range, region, language, shopping behavior, and preferred stores |
| [zazasync-watchlist.html](./zazasync-watchlist.html) | Watchlist page for saved products, alert toggles, recent activity, and notification settings |
| [zazasync-webmaster-brief.html](./zazasync-webmaster-brief.html) | HTML implementation brief for the webmaster/developer |
| [zazasync-mobile.html](./zazasync-mobile.html) | Mobile/PWA-style version of the inventory, watchlist, alerts, and profile experience |
| [zazasync-mobile-auth.html](./zazasync-mobile-auth.html) | Mobile sign-in/create-account page |
| [zazasync-mobile-onboarding.html](./zazasync-mobile-onboarding.html) | Mobile onboarding survey after account creation |
| [zazasync-age-gate.html](./zazasync-age-gate.html) | Future 21+ age verification entry page for the mobile/PWA product |
| [zazasync-mobile-product.html](./zazasync-mobile-product.html) | Future mobile product detail page with availability and alert options |
| [zazasync-sms-upsell.html](./zazasync-sms-upsell.html) | Future-only SMS alert upsell page; do not wire payments/SMS yet |
| [zazasync-pwa-manifest.json](./zazasync-pwa-manifest.json) | Future PWA manifest for installable mobile web app behavior |
| [zazasync-sw.js](./zazasync-sw.js) | Future service worker for caching and push-notification behavior |
| [FUTURE_PRODUCT_README.md](./FUTURE_PRODUCT_README.md) | Notes for the monetizable mobile-first product package |
| [MONETIZATION_PLAN.md](./MONETIZATION_PLAN.md) | Clean business monetization plan: reports first, B2B dashboard later, SMS future only |
| [WEBMASTER_HANDOFF.md](./WEBMASTER_HANDOFF.md) | File map explaining which pages belong together and what each page should become |
| [zazasync-web-v2.html](./zazasync-web-v2.html) | Latest preferred visual direction: clean search-first desktop web prototype |
| [TEAM_BRIEF.md](./TEAM_BRIEF.md) | Team product brief with strategy, UX flow, MVP priorities, and next decisions |

## Mobile Handoff

The mobile files are the phone/PWA version of the same product flow:

```text
zazasync-mobile.html
  -> main mobile app shell
  -> inventory search
  -> watchlist tab
  -> alerts tab
  -> profile tab

zazasync-mobile-auth.html
  -> mobile login/signup
  -> 21+ confirmation
  -> email/password or future OAuth

zazasync-mobile-onboarding.html
  -> first-time profile setup
  -> age range, region, language, frequency, preferred stores
  -> redirects back to zazasync-mobile.html
```

The webmaster should treat the desktop and mobile packages as the same product expressed in two layouts. They should share the same future backend data: users, profiles, products, stores, inventory, watchlist, alerts, and notification logs.

## Future Monetization Package

The future product files add the monetization direction:

```text
zazasync-age-gate.html
  -> 21+ access control before cannabis inventory

zazasync-mobile-product.html
  -> product detail and alert options

zazasync-sms-upsell.html
  -> future SMS alert upgrade concept only

zazasync-pwa-manifest.json + zazasync-sw.js
  -> installable PWA and push-notification foundation
```

Read [FUTURE_PRODUCT_README.md](./FUTURE_PRODUCT_README.md) before building this part. For the current build, SMS, Stripe, and Twilio should remain `coming soon`; the webmaster should focus on email alerts first.

For the business model, read [MONETIZATION_PLAN.md](./MONETIZATION_PLAN.md). The recommended monetization path is aggregated market intelligence reports first, not SMS.

## Preferred UX

The new web direction should feel like a focused product marketplace:

- Big search bar on the homepage
- Quick filters such as `In stock`, `New drops`, `Back in stock`, `Under $25`, `Pre-rolls`, and `CBD`
- Product cards with brand, product name, format, price, THC/CBD, and stock status
- Recently restocked products
- Email alert capture for out-of-stock products
- Stores with the most availability
- Clear 21+ and SQDC independence disclaimer

## Main User Flow

1. User lands on ZazaSync.
2. User searches by product, brand, price, potency, or category.
3. ZazaSync shows simple product cards.
4. User opens a product to see availability by SQDC store.
5. If the product is out of stock, user taps `Alert me`.
6. User enters an email for alerts.
7. ZazaSync notifies the user by email when the product appears available again.

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
7. SMS alerts later, after email alerts are working and the business is ready for paid notifications

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
