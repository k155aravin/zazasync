# ZazaSync Future Product Package

This package is the future mobile-first, monetizable version of ZazaSync. It should be treated as a product direction for later, not as the current webmaster build scope.

## Files In This Package

| File | Purpose |
|---|---|
| `zazasync-age-gate.html` | Age verification entry page for Quebec 21+ access |
| `zazasync-mobile-product.html` | Mobile product detail page with availability, sharing, and alert options |
| `zazasync-sms-upsell.html` | Future SMS alert upgrade / monetization page; keep as coming soon for now |
| `zazasync-pwa-manifest.json` | PWA manifest for installable mobile web app behavior |
| `zazasync-sw.js` | Service worker for offline cache and push-notification handling |

## Intended Product Flow

```text
User opens ZazaSync on mobile
  -> zazasync-age-gate.html
  -> user confirms 21+
  -> zazasync-mobile.html
  -> user searches/browses inventory
  -> user opens a product
  -> zazasync-mobile-product.html
  -> user sets email alert
  -> zazasync-sms-upsell.html
  -> future option: user upgrades to SMS alerts later
```

## Future Monetization Idea

The main future monetizable feature is SMS alerts. This is not part of the current build. The webmaster should leave SMS as `coming soon` and build email alerts first.

Free tier:

- Browse products
- Save products
- Email back-in-stock alerts
- Basic watchlist

Future paid/premium tier:

- SMS back-in-stock alerts
- Faster notification promise
- Preferred-store-only alerts
- Price drop SMS alerts
- Strict monthly SMS limits to control cost

## Webmaster Notes

The SMS page is currently a prototype. It does not process payment yet and does not send real SMS. Do not wire Stripe, Twilio, or paid SMS in the current build.

To make SMS production-ready later, the webmaster/developer will need:

- Payment provider, likely Stripe Billing with Checkout Sessions
- SMS provider, likely Twilio
- Verified phone number flow
- Clear SMS opt-in consent
- STOP/unsubscribe handling
- Alert throttling so costs do not explode
- Notification logs so the same alert is not sent repeatedly

Future Stripe recommendation:

- Use Stripe Billing for recurring SMS premium plans.
- Use Checkout Sessions with `mode: subscription` for signup/payment.
- Use Stripe Prices, not deprecated Plans.
- Use Stripe Customer Portal for cancellation, payment method updates, and subscription changes.
- Do not build manual renewal loops with raw PaymentIntents.

## Required Backend Tables

```text
users
profiles
products
stores
inventory
watchlist
alerts
subscriptions
notification_logs
user_events
```

## Required PWA Assets

The manifest references these icon files:

```text
/icons/icon-192.png
/icons/icon-512.png
```

Those icons were not included in the zip. The webmaster should create/add them before enabling the PWA manifest in production.

## Service Worker Notes

`zazasync-sw.js` is a prototype service worker for:

- caching static mobile files
- network-first fetch behavior
- push notification display
- opening the product page when a notification is clicked

Before production, the webmaster should confirm:

- cache paths match deployed routes
- push notification payload format matches the backend
- old caches are versioned and cleared safely
- service worker is registered only on the production mobile/PWA pages

## Compliance / Trust Notes

Because ZazaSync relates to cannabis and user notifications:

- Keep the 21+ age gate.
- Use clear SMS consent language.
- Include STOP/unsubscribe instructions in SMS.
- Keep SMS messages short to avoid multi-segment costs.
- Do not sell identifiable user data.
- Use aggregated/anonymized analytics only.

## Recommended Build Order

1. Finish free email alerts.
2. Add product detail page.
3. Add age gate before cannabis inventory access.
4. Add SMS upsell page.
5. Leave SMS upsell as coming soon.
6. Enable PWA manifest and service worker when production routes are ready.
7. Later: connect Stripe subscriptions or paid SMS credits.
8. Later: connect Twilio SMS delivery.
9. Later: add throttling, notification logs, and STOP handling.

## Simple Summary

This future package is the monetization direction:

```text
Age gate
  -> Mobile product page
  -> Email alerts
  -> SMS upsell as coming soon
  -> Paid SMS alerts later
  -> PWA install/push notification support
```

It should connect to the same backend as the existing desktop and mobile handoff pages.
