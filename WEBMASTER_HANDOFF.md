# ZazaSync Webmaster Handoff

This document explains how the current prototype files fit together so the webmaster can turn them into a working site.

## Main File Set

These files belong together and should be treated as the current web handoff package:

| File | Role | Connects To |
|---|---|---|
| `zazasync.html` | Main inventory homepage and search-first landing page | `zazasync-auth.html`, future product pages, future inventory data |
| `zazasync-auth.html` | Sign in / create account page | `zazasync-onboarding.html`, `zazasync-watchlist.html` |
| `zazasync-onboarding.html` | First-time user onboarding survey | `zazasync-watchlist.html` |
| `zazasync-watchlist.html` | User watchlist, saved products, alert settings | `zazasync.html`, auth/user database, product inventory data |
| `zazasync-webmaster-brief.html` | Technical implementation brief for the webmaster | Use as a developer checklist |

## Mobile File Set

These files are the mobile/PWA version of the same product. They should connect to the same backend as the desktop web files, not a separate database.

| File | Role | Connects To |
|---|---|---|
| `zazasync-mobile.html` | Mobile app shell with inventory, watchlist, alerts, and profile tabs | Product data, inventory data, watchlist, alerts |
| `zazasync-mobile-auth.html` | Mobile sign in / create account page | `zazasync-mobile-onboarding.html`, auth provider |
| `zazasync-mobile-onboarding.html` | Mobile first-time onboarding survey | `zazasync-mobile.html`, user profile database |

Mobile user flow:

```text
zazasync-mobile.html
  -> user searches/browses products on phone
  -> user taps watchlist/alerts/profile or signs up
  -> zazasync-mobile-auth.html
  -> new user creates account and confirms 21+
  -> zazasync-mobile-onboarding.html
  -> user chooses age range, region, language, shopping frequency, preferred stores
  -> zazasync-mobile.html
  -> user manages watchlist, alerts, and profile from tabs
```

Important: the mobile files are not a separate app yet. They are a mobile-first web/PWA prototype. A webmaster can either:

- keep them as standalone mobile HTML pages,
- merge them into responsive routes in the main site,
- or rebuild them as React/Next.js mobile views using the same design and flow.

## Future Monetizable Mobile Package

These files are the future product/monetization layer. They are not a separate product; they should be wired into the same ZazaSync account, product, inventory, watchlist, and alert system.

| File | Role | Build Notes |
|---|---|---|
| `zazasync-age-gate.html` | 21+ gate before cannabis inventory access | Keep before public/mobile cannabis inventory views |
| `zazasync-mobile-product.html` | Mobile product detail page | Connect to real product, store availability, watchlist, and alert data |
| `zazasync-sms-upsell.html` | SMS alert monetization page | Connect to Stripe/payment and Twilio/SMS provider later |
| `zazasync-pwa-manifest.json` | PWA install manifest | Requires missing `/icons/icon-192.png` and `/icons/icon-512.png` assets |
| `zazasync-sw.js` | Service worker for cache and push notification behavior | Register only after production routes and cache paths are confirmed |
| `FUTURE_PRODUCT_README.md` | Full notes for the monetizable package | Read before implementation |

Future monetization flow:

```text
Age gate
  -> Mobile inventory
  -> Product detail
  -> Email alert
  -> SMS upsell
  -> Paid SMS alerts
  -> PWA/push support later
```

Important for the webmaster:

- SMS alerts are not just a UI toggle. They need backend alert logic, consent, STOP handling, and notification logs.
- Start with email alerts first, then add SMS once the alert logic works.
- SMS should be limited or premium because every message has a cost.
- For recurring SMS premium plans, use Stripe Billing with Checkout Sessions and Stripe Prices.
- Use Stripe Customer Portal for self-service cancellation and payment updates.
- The PWA manifest references icon files that are not currently included.
- The service worker is a prototype and must be tested against production routes before launch.

## User Flow

The intended user journey is:

```text
zazasync.html
  -> user searches/browses products
  -> user clicks Sign in or Get alerts
  -> zazasync-auth.html
  -> new user creates account
  -> zazasync-onboarding.html
  -> user chooses age range, region, language, frequency, preferred stores
  -> zazasync-watchlist.html
  -> user manages saved products and alert settings
```

Returning users can go:

```text
zazasync-auth.html
  -> sign in
  -> zazasync-watchlist.html
```

## What Each Page Should Become

### `zazasync.html`

Purpose: public-facing search and inventory discovery.

Build work:

- Connect search to real product data.
- Make navigation links go to real routes.
- Make `Sign in` open the auth page.
- Make `Get alerts` open signup/auth or an alert capture flow.
- Product cards should eventually link to real product detail pages.
- `Watchlist` nav should require login and go to the watchlist page.

Suggested production route:

```text
/
/inventory
```

### `zazasync-auth.html`

Purpose: account creation and login.

Build work:

- Connect email/password sign in.
- Connect Google OAuth if desired.
- Enforce 21+ confirmation on signup.
- After signup, redirect to onboarding.
- After login, redirect to watchlist if onboarding is complete.

Suggested production routes:

```text
/signin
/signup
/auth
```

### `zazasync-onboarding.html`

Purpose: capture profile/preferences that make alerts and analytics useful.

Build work:

- Save onboarding answers to the user profile.
- Capture age range, region, language, shopping frequency, and preferred stores.
- Do not collect exact birthdate unless legally necessary.
- After completion, mark `onboarding_done = true`.
- Redirect to watchlist.

Suggested production route:

```text
/onboarding
```

### `zazasync-watchlist.html`

Purpose: user dashboard for saved products and alerts.

Build work:

- Load saved products for the signed-in user.
- Show in-stock and out-of-stock watched products.
- Allow add/remove from watchlist.
- Allow alert toggles for email and later SMS.
- Show recent activity such as restocked, price drop, or alert sent.

Suggested production route:

```text
/watchlist
```

### `zazasync-webmaster-brief.html`

Purpose: developer-facing implementation notes.

Build work:

- Use this file as a checklist.
- It explains auth, onboarding, watchlist, alert logic, event tracking, and suggested database tables.
- It does not need to be a public user page.

Suggested production route:

```text
/webmaster-brief
```

Or keep it private/internal only.

## Older / Supporting Files

These files are useful, but they are not the main current handoff package:

| File | Role |
|---|---|
| `zazasync-web-v2.html` | Earlier copy of the search-first design direction |
| `TEAM_BRIEF.md` | Product strategy and team discussion notes |
| `ZazaSync_Team_Product_Brief.docx` | Word version of the product brief |
| `scripts/build_zazasync_team_doc.py` | Script used to generate the Word brief |

## Suggested Folder Structure For Production

The webmaster can keep the prototype files in root for now, but a production app should eventually be organized like this:

```text
/
  index.html or app entry
  pages/
    inventory
    auth
    onboarding
    watchlist
    product-detail
  components/
    nav
    product-card
    alert-modal
    store-availability
  data/
    products
    stores
    inventory
    alerts
```

If using React/Next.js, the pages would become routes instead of raw HTML files.

## Backend / Database Pieces Needed

The frontend pages need these data areas:

| Area | Purpose |
|---|---|
| Users | Login, signup, profile, age confirmation |
| Products | SQDC product catalog |
| Stores | SQDC locations |
| Inventory | Product availability by store |
| Watchlist | Products saved by each user |
| Alerts | Email/SMS notification preferences |
| Subscriptions | Paid SMS alerts, plan status, Stripe customer/subscription IDs |
| Notification logs | Prevent repeat SMS/email spam and track delivery history |
| Events | Search, product views, watchlist adds, alert sets |

## Suggested Database Tables

```text
users
profiles
products
stores
inventory
watchlist
alerts
subscriptions
user_events
notification_logs
```

## What To Build First

Recommended order:

1. Make `zazasync.html` the working homepage.
2. Wire sign in / signup from `zazasync-auth.html`.
3. Save onboarding data from `zazasync-onboarding.html`.
4. Connect `zazasync-watchlist.html` to real user data.
5. Add email alerts for out-of-stock products.
6. Add SMS later.

## Important Privacy Note

ZazaSync can collect useful user preferences, but user data should be handled carefully.

Recommended:

- Use age ranges, not exact age, unless exact DOB is legally required.
- Use region/city, not exact home address.
- Ask for clear consent before using activity for analytics.
- Sell/report only anonymized aggregate insights.
- Do not sell identifiable user profiles.

## Simple Summary

The current file package should be understood like this:

```text
Public product search:
  zazasync.html

Account system:
  zazasync-auth.html

First-time profile setup:
  zazasync-onboarding.html

Saved products and alerts:
  zazasync-watchlist.html

Developer instructions:
  zazasync-webmaster-brief.html
```

That is the complete handoff set.

## Desktop vs Mobile Relationship

The desktop and mobile files should represent the same product logic:

| Product Concept | Desktop File | Mobile File |
|---|---|---|
| Inventory/search | `zazasync.html` | `zazasync-mobile.html` |
| Auth/signup | `zazasync-auth.html` | `zazasync-mobile-auth.html` |
| Onboarding/profile setup | `zazasync-onboarding.html` | `zazasync-mobile-onboarding.html` |
| Watchlist/alerts | `zazasync-watchlist.html` | `zazasync-mobile.html` tabs |
| Developer notes | `zazasync-webmaster-brief.html` / `WEBMASTER_HANDOFF.md` | Same notes apply |

Build once, share data everywhere. The frontend can have different layouts, but the backend should be one system.
