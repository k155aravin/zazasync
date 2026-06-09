# ZazaSync Webmaster Pre-Payment Corrections

**Prepared:** June 8, 2026

**Live site:** https://zazasync.com

**Purpose:** Required corrections and acceptance checks before the current website work is considered complete.

This document records the agreed product and technical corrections following a review of the live website and GitHub repository. Please complete each item, deploy it to production, and provide the requested evidence.

## 1. Store Inventory Browsing

### Current issue

Some homepage store cards link to `/stores/undefined`. Selecting a store must do more than open the general Stores page.

### Required result

Each store card must link to that store's dedicated page. The store page must:

- show the selected store name, city, and latest successful check time;
- show products associated with that store;
- display available products first;
- group or filter products by useful categories such as dried flower, pre-rolls, extracts, edibles, beverages, vapes, oils, and accessories;
- provide search and filters for category, price, THC, CBD, format, and availability;
- label every product as `Available`, `Low stock`, `Unavailable`, `Not confirmed`, or `Stale`, based only on supported data;
- allow a signed-in user to save or request an email alert for an unavailable product.

### Acceptance evidence

- No production link contains `/stores/undefined`.
- Demonstrate at least three homepage store links opening the correct store.
- Demonstrate category browsing and availability filtering inside one store.

## 2. Domain Access and Redirect

### Current issue

`https://zazasync.com` works, but `www.zazasync.com` does not resolve.

### Required result

Configure Cloudflare DNS and a permanent redirect so:

```text
https://www.zazasync.com -> https://zazasync.com
```

Both the `www` and non-`www` addresses must safely land on the same production website.

### Acceptance evidence

- `www.zazasync.com` resolves successfully.
- It redirects to `https://zazasync.com` using a permanent redirect.

## 3. Contact and Profile Pages

### Contact page

Create the public route:

```text
https://zazasync.com/contact
```

The active Zoho mailbox is:

```text
support@zazasync.com
```

The page must:

- display `support@zazasync.com` as the direct contact method;
- include name, email, subject/reason, and message fields;
- include reasons such as support, incorrect product data, business inquiry, and privacy/account request;
- deliver valid form submissions to `support@zazasync.com`;
- show a clear success or failure response;
- validate and sanitize submissions;
- use spam protection such as Cloudflare Turnstile and server-side rate limiting;
- keep Zoho credentials and other secrets out of browser code and GitHub.

### Profile page

Create the authenticated route:

```text
https://zazasync.com/profile
```

It must allow signed-in users to:

- update their name and profile preferences;
- update age range, region, and language;
- manage preferred SQDC stores;
- manage email-alert preferences;
- request a personal-data export;
- request or complete account deletion;
- sign out.

Unsigned users must be redirected to:

```text
/login?redirect=/profile
```

### Acceptance evidence

- `/contact` and `/profile` no longer return 404.
- Submit a production contact test and confirm receipt at `support@zazasync.com`.
- Demonstrate authenticated profile updates persisting after sign-out/sign-in.

## 4. Correct Privacy Contact

### Current issue

The Privacy Policy uses `privacy@zazasync.ca`. The `.ca` domain does not exist.

### Required result

Remove `privacy@zazasync.ca` everywhere and use the active address:

```text
support@zazasync.com
```

This address should be identified for:

- privacy questions;
- data correction;
- personal-data export;
- consent withdrawal;
- account deletion.

No additional privacy alias is required for the current release.

### Acceptance evidence

- Repository and production search show no remaining reference to `privacy@zazasync.ca`.
- The Privacy Policy displays `support@zazasync.com`.

## 5. Fixed Terms Update Date

### Current issue

The Terms page says `Last updated: today`. The meaning changes every 24 hours and falsely implies that the Terms were revised on the visitor's current date.

### Required result

Use a fixed publication or revision date, for example:

```text
Last updated: June 8, 2026
```

Change this date only when the Terms are genuinely revised. Keep prior versions internally and notify users when a material change affects their rights, privacy, or account usage.

### Acceptance evidence

- The production Terms page uses a complete fixed date.
- The implementation does not generate the value from the current date.

## 6. PWA Manifest, Icons, and Unified Branding

### Current issue

The expected PWA manifest and icon routes return 404. The website also uses inconsistent bright-green and older dark-green brand variations.

### Required result

Use the current bright-green ZazaSync symbol from the live website as the official mark. Create one approved master logo and export:

```text
/icons/icon-192.png
/icons/icon-512.png
/icons/icon-maskable-512.png
```

Publish and connect:

```text
/manifest.webmanifest
```

The manifest must define the correct ZazaSync name, start URL, standalone display mode, theme/background colours, language, and icons.

Use the same official mark consistently in:

- navigation;
- age gate;
- login and signup;
- mobile experience;
- favicon;
- installed PWA.

Provide the owner with the original master logo file. Push notifications remain future scope and are not required for this correction.

### Acceptance evidence

- Manifest and icon URLs return HTTP 200.
- Browser application inspection recognizes the manifest and icons.
- Demonstrate Add to Home Screen using the correct ZazaSync icon.

## 7. Mobile-First, Synchronized Experience

### Current issue

The public `/mobile-app` page contains prototype products that do not match the real inventory. It feels like a separate product from the main website.

### Product direction

Mobile is the primary ZazaSync experience because most users are expected to visit from phones. Desktop is the expanded version of the same product.

### Required result

- Use the same live product, store, availability, account, watchlist, and alert data on desktop and mobile.
- Remove all fake or prototype product content from public pages.
- Make the main application fully responsive instead of maintaining a disconnected mobile product.
- Keep search immediately accessible.
- Use compact product cards, large touch targets, and one-handed navigation.
- Provide a useful mobile bottom navigation for Inventory, Stores, Watchlist, Alerts, and Profile.
- Use bottom sheets or similarly efficient controls for filters.
- Keep important product actions, such as Save or Alert me, easily accessible.
- Prevent horizontal overflow, overlapping text, and oversized headings.

Connect `/mobile-app` to the real application, remove it from public navigation, or redirect it to the real responsive experience.

### Acceptance evidence

- No fake product appears on public mobile routes.
- Demonstrate identical product prices and availability on desktop and mobile.
- Test common iPhone and Android viewport sizes.
- Provide mobile screenshots for homepage, inventory, product, store, watchlist, and profile.

## 8. React Hydration Error

### Current issue

The production browser console repeatedly reports:

```text
Minified React error #418
```

This indicates that server-rendered HTML does not match the browser's first React render. It can cause flashing, layout movement, delayed interaction, incorrect age-gate/auth state, and unreliable first taps on slower phones.

### Required result

Run a development build to identify the exact component mismatch. Review:

- age-gate and local-storage state;
- authentication state;
- date, time, locale, and timezone formatting;
- browser-only values rendered on the server;
- random or changing initial values;
- invalid HTML nesting.

Browser-only values should be introduced after hydration where appropriate. Server and browser must produce matching initial markup.

### Acceptance evidence

Provide:

- the identified root cause;
- the corrected component/file;
- before-and-after console evidence;
- production tests for anonymous, returning, and signed-in users;
- a clean production console with no hydration errors.

## 9. Mobile Performance and Core Web Vitals

### Current issue

During review, the homepage response was approximately 2.56 MB of HTML, plus approximately 475 KB of JavaScript and 177 KB of CSS. Initial response time was about 2.5 seconds and may be worse on cellular connections.

### Required result

- Do not embed the complete inventory dataset in initial homepage HTML.
- Render only the content needed above the fold.
- Load additional products with queries, pagination, or incremental loading.
- Compress, resize, and lazy-load product images.
- Split JavaScript by route and remove unused code.
- Remove unused CSS.
- configure appropriate Cloudflare caching and compression;
- preload only critical assets.

### Acceptance targets

- Largest Contentful Paint below 2.5 seconds.
- Interaction to Next Paint below 200 milliseconds.
- Cumulative Layout Shift below 0.1.
- Mobile Lighthouse Performance score of at least 85, preferably 90 or higher.

Provide a production Lighthouse report and real mobile Core Web Vitals evidence where available.

## 10. Availability Consistency and Restock History

### Current issue

Product and store pages can present conflicting availability information. Unknown or unconfirmed checks must not be treated as available or unavailable.

### Required status model

- `Available`: positive evidence from the latest successful check.
- `Low stock`: only when the source provides reliable low-stock evidence.
- `Unavailable`: positive evidence that the product is unavailable.
- `Not confirmed`: the latest check did not provide reliable evidence.
- `Stale`: the evidence is older than the accepted freshness window.

Use one documented calculation across the homepage, inventory, product pages, store pages, watchlist, and alerts. Every status should include the last successful check and a direct SQDC verification link.

ZazaSync must retain previous product/store snapshots so it can detect:

```text
Unavailable -> Available = Restock
```

On a restock:

1. Save the change event.
2. Find users watching the product and relevant store.
3. Queue one email notification.
4. Send the notification.
5. Log the result to prevent duplicates.

### Acceptance evidence

- Provide the documented status rules.
- Demonstrate one product/store history transition.
- Demonstrate a complete test from unavailable state to a real received email at a test address.
- Show duplicate-alert prevention.

## 11. B2B Illustrative Data Labels

### Current issue

The `/for-brands` page displays example figures such as `2,847 searches`, `1,203 watchlist saves`, and `847 active alerts`. These are not currently verified live ZazaSync statistics.

### Required result

Add a prominent notice near the beginning of the page:

> All figures displayed are illustrative sample data and are not live ZazaSync statistics.

Also label every example statistic, chart, dashboard preview, recommendation, and report excerpt as:

```text
Sample data
Illustrative example
Demo figures - not live data
```

Do not present figures as verified until event tracking, consent, aggregation, minimum cohort sizes, privacy review, and reliable reporting are operational.

### Acceptance evidence

- Every fictional statistic is visibly labelled.
- No page implies that sample figures represent real customers or demand.

## 12. Search Discovery and Security Files

### Current issue

These standard routes return 404:

```text
/robots.txt
/sitemap.xml
/.well-known/security.txt
```

### Required result

`robots.txt` must guide search crawlers and block private or internal areas such as account, admin, and authentication-processing routes.

`sitemap.xml` must include public pages, products, stores, New Drops, Terms, Privacy, and other indexable content. It should update automatically as public products and stores change.

`security.txt` must explain how vulnerabilities can be reported and use:

```text
support@zazasync.com
```

### Acceptance evidence

- All three routes return HTTP 200.
- The sitemap contains valid production URLs.
- Private account or administration routes are not included in the sitemap.

## Final Acceptance Package

After completing the corrections, provide:

1. The complete source code used to deploy `zazasync.com` in this GitHub repository.
2. Environment-variable documentation with no secrets committed.
3. Database migrations and Supabase Row Level Security policies.
4. Deployment and rollback instructions.
5. A production test report completed against `https://zazasync.com`.
6. Evidence requested under each numbered correction.
7. Confirmation that the owner controls Cloudflare, Supabase, Zoho, hosting, analytics, and recovery/billing access.

Final approval should be based on the live production result and reproducible GitHub source, not screenshots or staging-only tests.
