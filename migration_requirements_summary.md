# ZazaSync Migration Requirements Summary

This task is a UI migration and integration effort, not a replacement of the old working application with a static shell. The GitHub prototype files define the desired visual interface, while the site must preserve the working behavior users already expect: inventory browsing from real SQDC product data, navigation between pages, account creation and sign-in, onboarding, saved watchlist products, and email-based back-in-stock alerts.

## Required public routes

| Route | Source prototype | Expected behavior |
|---|---|---|
| `/` | `zazasync.html` | Search-first inventory homepage using real product data. |
| `/inventory` | `zazasync.html` | Same inventory experience as homepage, with filters and product grid. |
| `/auth` | `zazasync-auth.html` | Sign-in and sign-up screen wired to authentication. |
| `/signin` | `zazasync-auth.html` | Sign-in route alias. |
| `/signup` | `zazasync-auth.html` | Sign-up route alias. |
| `/onboarding` | `zazasync-onboarding.html` | Post-signup profile/preferences survey. |
| `/watchlist` | `zazasync-watchlist.html` | Authenticated saved-products and alert-management page. |
| `/webmaster-brief` | `zazasync-webmaster-brief.html` | Developer reference page; can remain internal. |

## Functional requirements

The homepage must use the real scraped SQDC dataset already seeded into D1, not placeholder-only content. Navigation links must point to functional Worker routes. Product cards should expose product IDs or slugs so watchlist and alert actions can bind to real records. Authentication should use the existing Supabase-backed account model if credentials are available; otherwise, staging should expose a clear configuration requirement rather than pretending auth works. The sign-up flow must enforce a 21+ age confirmation before account creation and redirect new users to onboarding. Returning users should be able to sign in and reach the watchlist.

The watchlist must load saved products for the authenticated user, allow products to be saved or removed, and support email alert toggles. SMS must remain disabled or marked as coming soon. Onboarding must save profile preferences, including age range, region, language, shopping frequency, preferred stores, email-alert preference, and an onboarding completion flag. Event tracking and alert logs are important for later monetization, but the immediate staging goal is to make navigation, data rendering, auth, onboarding, and watchlist behavior demonstrably functional.

## Safety constraints

Production should not be touched until staging has been verified. The previous production deployment is already broken for core interactions, so all new changes must first deploy to the staging Worker and be tested there. If Supabase URL and anon key cannot be recovered from local legacy assets, the next safe step is to ask the user for them before claiming auth or watchlist functionality is restored.
