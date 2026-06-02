# ZazaSync Monetization Plan

## Summary

ZazaSync is free for consumers at first. The business value comes from anonymized, aggregated market intelligence about Quebec SQDC product demand.

The core idea:

> Users get a useful product search, watchlist, and email alert tool. ZazaSync learns what products, brands, categories, regions, and price ranges people care about. Brands can pay for aggregated market intelligence, never individual user data.

## Current Build Scope

The webmaster should focus on the current product loop:

```text
Search products
  -> View availability
  -> Save to watchlist
  -> Set email alert
  -> Complete onboarding profile
```

Current priority:

1. Product search and inventory browsing
2. Product detail pages
3. User accounts
4. Onboarding profile
5. Watchlist
6. Email back-in-stock alerts
7. Aggregated analytics foundation

SMS, Stripe, Twilio, paid alerts, and subscriptions are future only. Do not build them now.

## What Makes The Data Valuable

SQDC inventory visibility helps consumers, but the larger business opportunity is market intelligence.

Cannabis producers and brands often want to understand:

- Which products people search for
- Which brands get the most attention
- Which products people save to a watchlist
- Which products trigger the most back-in-stock alerts
- Which regions show the highest demand
- Which age ranges prefer specific categories
- Which price ranges users filter for
- Which products go out of stock fastest

ZazaSync can help answer those questions using aggregated and anonymized data.

## What Data We Can Collect

### Profile Data

Collected through onboarding:

| Data Point | Collection Method | Business Value |
|---|---|---|
| Age range | Onboarding survey | Demographic demand trends |
| Region | Onboarding survey | Regional demand trends |
| Visit frequency | Onboarding survey | Casual vs frequent shopper segments |
| Language preference | Onboarding survey | French/English experience planning |
| Preferred stores | Onboarding survey | Store-level demand patterns |
| Signup date | Account creation | Cohort analysis |

Important: use age ranges, not exact age, unless exact date of birth is legally required.

### Behavioral Data

Collected through product usage:

| User Action | Signal |
|---|---|
| Search query | Product/category/brand interest |
| Product page view | Product interest |
| Watchlist add | Strong product demand |
| Email alert set | High purchase intent |
| Price filter click | Budget sensitivity |
| Category filter click | Category preference |
| Store filter click | Location preference |

This data should be used only in aggregated and anonymized form for external reporting.

## Revenue Stream 1: Monthly Market Intelligence Reports

This is the best first monetization path because it does not require SMS, payments inside the app, or consumer subscriptions.

What it is:

Monthly PDF or dashboard-style reports sold to cannabis producers, brands, or agencies operating in Quebec.

Possible report sections:

- Most searched products
- Most watchlisted products
- Products with the most alert demand
- Demand by region
- Demand by age range
- Category trends
- Price sensitivity
- New drop interest
- Restock demand
- Brand comparison

Example safe insight:

> In Montreal, users aged 26-44 created more watchlist alerts for pre-rolls under $20 than for any other category this month.

Do not include names, emails, phone numbers, or individual user behavior.

Possible pricing assumptions:

| Report Type | Possible Price Range | Notes |
|---|---:|---|
| Single brand report | $500-$1,500 | Focused on one producer/brand |
| Category report | $800-$2,000 | Example: pre-rolls, flower, CBD |
| Full Quebec market report | $2,000-$5,000 | Larger monthly market readout |
| Custom deep-dive report | $3,000-$8,000 | One-time custom analysis |

These are assumptions, not guaranteed pricing.

## Revenue Stream 2: Future B2B Dashboard

This should come after reports prove demand.

What it is:

A private login dashboard where brands can view aggregated demand signals for their products and categories.

Possible dashboard modules:

- Search interest by product
- Watchlist count by product
- Alert count by product
- Regional demand
- Age-range demand
- Category comparisons
- 30/60/90 day trends
- Restock-demand signals

Possible plan assumptions:

| Plan | Possible Price | Included |
|---|---:|---|
| Starter | $299/month | Limited SKUs, monthly email report |
| Brand | $599/month | More SKUs, dashboard access |
| Enterprise | Custom | Multi-brand or agency view |

This is future SaaS. Do not build the B2B dashboard before the consumer product and reports are working.

## Revenue Stream 3: Future Sponsored Placements

This is a later phase and should be handled carefully.

Possible placements:

- Featured product card
- New drop highlight
- Category page highlight
- Sponsored brand banner

Important requirements:

- Sponsored placements must be clearly labeled.
- Do not make medical or product claims.
- Do not imply ZazaSync sells cannabis.
- Keep user trust first.

## Revenue Stream 4: Future SMS Premium Alerts

SMS is future only.

Do not ask the webmaster to build SMS now.

When the product is mature, SMS could become a premium feature:

- Faster back-in-stock alerts
- Preferred-store-only alerts
- Price drop SMS alerts
- Monthly SMS limits

Future requirements:

- Stripe Billing or another payment system
- SMS provider such as Twilio
- Phone verification
- Explicit SMS opt-in
- STOP/unsubscribe handling
- Notification logs
- Alert throttling to control cost

For now:

```text
Email alerts = current build
SMS alerts = coming soon
```

## Data Flywheel

```text
Useful search and alerts
  -> More users
  -> More watchlist and alert signals
  -> Better aggregated market intelligence
  -> Better reports for brands
  -> Revenue supports better product
  -> More users
```

## Legal And Privacy Principles

What ZazaSync should never sell:

- Names
- Emails
- Phone numbers
- Individual profiles
- Individual browsing histories
- Any personally identifiable information

What ZazaSync may sell later:

- Aggregated market trends
- Anonymized demand statistics
- Regional/category/product trend reports
- Cohort-level insights where users cannot be identified

Recommended trust rules:

- Clear privacy policy
- Clear consent at signup
- User account deletion option
- Data export/delete request process
- No sale of identifiable user data
- Report only sufficiently large cohorts

## Who To Pitch First

Best early targets:

1. Quebec craft cannabis brands with several SQDC SKUs
2. Brands planning a Quebec launch
3. Marketing agencies representing cannabis brands
4. Mid-size producers trying to understand Quebec demand

Start with reports before dashboards.

## Example Brand Pitch

> ZazaSync shows Quebec cannabis demand from the consumer side: what people search, what they save, and what they want back in stock. We package that into anonymized regional and demographic market intelligence so brands can understand demand without accessing individual user data.

## Build Order For Monetization

1. Finish the consumer product search experience.
2. Add user accounts.
3. Add onboarding profile.
4. Add watchlist.
5. Add email back-in-stock alerts.
6. Log search, product view, watchlist, and alert events.
7. Build internal analytics summaries.
8. Produce first manual monthly report.
9. Sell reports to early brand/agency customers.
10. Build B2B dashboard only after reports prove demand.
11. Add sponsored placements later.
12. Keep SMS premium alerts as a future phase.

## Simple Takeaway

The first monetization path is not SMS.

The first monetization path is:

```text
Consumer product usage
  -> Aggregated demand data
  -> Monthly market intelligence reports
  -> Brand/agency customers
```

SMS can become a premium feature later, but the current webmaster build should focus on email alerts and clean data capture.
