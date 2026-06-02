# ZazaSync Future Product Package

This package is the future mobile-first, monetizable version of ZazaSync. It should be treated as a product direction for a production web/PWA build, not just a static design.

## Files In This Package

| File | Purpose |
|---|---|
| `zazasync-age-gate.html` | Age verification entry page for Quebec 21+ access |
| `zazasync-mobile-product.html` | Mobile product detail page with availability, sharing, and alert options |
| `zazasync-sms-upsell.html` | SMS alert upgrade / monetization page |
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
  -> user sets email alert or chooses SMS
  -> zazasync-sms-upsell.html
  -> user upgrades to SMS alerts
```

## Monetization Idea

The main monetizable feature is SMS alerts.

Free tier:

- Browse products
- Save products
- Email back-in-stock alerts
- Basic watchlist

Paid/premium tier:

- SMS back-in-stock alerts
- Faster notification promise
- Preferred-store-only alerts
- Price drop SMS alerts
- Strict monthly SMS limits to control cost

## Webmaster Notes

The SMS page is currently a prototype. It does not process payment yet and does not send real SMS.

To make it production-ready, the webmaster/developer needs:

- Payment provider, likely Stripe Billing with Checkout Sessions
- SMS provider, likely Twilio
- Verified phone number flow
- Clear SMS opt-in consent
- STOP/unsubscribe handling
- Alert throttling so costs do not explode
- Notification logs so the same alert is not sent repeatedly

Stripe recommendation:

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
5. Connect Stripe subscriptions or paid SMS credits.
6. Connect Twilio SMS delivery.
7. Add throttling, notification logs, and STOP handling.
8. Enable PWA manifest and service worker.

## Simple Summary

This future package is the monetization layer:

```text
Age gate
  -> Mobile product page
  -> Email alerts
  -> SMS upsell
  -> Paid SMS alerts
  -> PWA install/push notification support
```

It should connect to the same backend as the existing desktop and mobile handoff pages.
