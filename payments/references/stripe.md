# Stripe — Testing & Debugging Playbook

Scope: web payments and subscriptions (Checkout, Payment Intents, Billing).
For greenfield integration *design*, prefer the official `stripe-best-practices`
skill (`claude plugin install stripe@claude-plugins-official`); this file is the
debugging/testing companion. Latest API version at time of writing: `2026-06-24.dahlia`.

## API surface decision matrix (quick recall)

| Need | Use |
|------|-----|
| One-time payment, minimal code | Checkout Sessions (`mode=payment`, hosted or embedded) |
| Custom payment form | Checkout Sessions + Payment Element |
| Save card for later | Setup Intents (`mode=setup`) |
| Subscriptions | Billing APIs + Checkout Sessions (`mode=subscription`) |
| Customer self-serve (change plan, update card, cancel, invoices) | Billing Portal — `POST /v1/billing_portal/sessions`; default to this over custom UIs |
| Fully custom flow | Payment Intents (lower-level primitive) |

Do **not** pass `payment_method_types` — omit it and let dynamic payment methods
apply (use `payment_method_configurations` / `excluded_payment_method_types` to shape).

## Local webhook loop (the core dev workflow)

```bash
stripe login
stripe listen --forward-to localhost:4242/webhook
# prints: whsec_xxx  → use as STRIPE_WEBHOOK_SECRET while listening
stripe listen --forward-to localhost:4242/webhook \
  --events checkout.session.completed,invoice.paid,invoice.payment_failed
```

Fire synthetic events (creates real test-mode objects; cascading events fire too —
`payment_intent.succeeded` also emits `payment_intent.created`):

```bash
stripe trigger checkout.session.completed
stripe trigger invoice.payment_failed
stripe trigger --help                                  # list all triggerable events
stripe trigger payment_intent.succeeded --add payment_intent:customer=cus_xxx
stripe trigger invoice.paid --override plan:product.name=myProduct
stripe trigger customer.created --edit                 # edit fixture before firing
stripe trigger checkout.session.completed --stripe-account acct_xxx  # Connect
```

### Webhook handler checklist

- Verify with `stripe.webhooks.constructEvent(rawBody, sig, endpointSecret)` —
  **raw body**, not parsed JSON (framework body-parsers are the #1 breakage).
- Return 200 fast; do real work async. Stripe retries failed deliveries with
  exponential backoff for **3 days**.
- Deduplicate by `event.id`; events can arrive out of order — re-fetch the object
  when the current state matters.
- Dashboard → Developers → Webhooks → your endpoint shows delivery attempts,
  response codes, and lets you resend individual events.
- `invoice.created` special case: with auto-charge Stripe waits **1 hour** after a
  successful webhook response before charging; if no success within **72 hours**
  it finalizes anyway.

## Subscription lifecycle events (the ones that matter)

| Event | Fires when | Handler |
|-------|-----------|---------|
| `checkout.session.completed` | Checkout finishes | Provision; retrieve session with `subscription`/`customer` expanded |
| `customer.subscription.created` | Sub created (may be `incomplete` if SCA pending) | Store record |
| `customer.subscription.updated` | Plan/coupon/status change | Sync DB state |
| `customer.subscription.deleted` | Canceled/ended | Revoke access |
| `customer.subscription.trial_will_end` | 3 days before trial end | Check payment method, notify |
| `customer.subscription.paused` / `.resumed` | Trial ended w/o PM / resumed | Pause/restore access |
| `invoice.paid` | Payment succeeds | **Canonical renewal-provision event** — extend expiry |
| `invoice.payment_failed` | Payment fails | Notify, collect new PM; enable Smart Retries |
| `invoice.payment_action_required` | 3DS/SCA needed | Prompt customer to authenticate |
| `invoice.upcoming` | N days pre-renewal | Optionally add invoice items |
| `charge.dispute.created` | Chargeback | Flag account, submit evidence |

Statuses: `trialing → active`; `incomplete` (23h to complete payment) →
`incomplete_expired`; failed renewals → `past_due` → `unpaid`/`canceled` per
Billing settings; `paused`.

## Test cards (test mode; any future expiry, any CVC)

| Scenario | Number |
|----------|--------|
| Success (Visa) | `4242 4242 4242 4242` |
| Success (MC / Amex) | `5555555555554444` / `378282246310005` |
| Generic decline | `4000000000000002` |
| Insufficient funds | `4000000000009995` |
| Lost / stolen | `4000000000009987` / `4000000000009979` |
| Expired / bad CVC | `4000000000000069` / `4000000000000127` |
| 3DS: always authenticate | `4000002760003184` |
| 3DS: authenticate unless set up | `4000002500003155` |
| Radar: always blocked / highest risk | `4100000000000019` / `4000000000004954` |
| Dispute: fraudulent / not received | `4000000000000259` / `4000000000002685` |

In API calls prefer PaymentMethod shortcuts (`pm_card_visa`, `pm_card_chargeDisputed`)
over raw numbers. Real card data in test mode violates ToS.

## Test clocks — simulate months of renewals in seconds

Sandbox-only time travel for Billing objects:

```bash
# 1. Create a frozen clock
curl https://api.stripe.com/v1/test_helpers/test_clocks -u "$STRIPE_TEST_KEY:" \
  -d frozen_time=1782000000 -d "name=renewal-sim"        # → clock_xxx
# 2. Create customer+sub attached to the clock
curl https://api.stripe.com/v1/customers -u "$STRIPE_TEST_KEY:" \
  -d email=t@example.com -d test_clock=clock_xxx \
  -d payment_method=pm_card_visa -d "invoice_settings[default_payment_method]=pm_card_visa"
# 3. Advance time (forward only) and watch webhooks fire
curl https://api.stripe.com/v1/test_helpers/test_clocks/clock_xxx/advance \
  -u "$STRIPE_TEST_KEY:" -d frozen_time=1784700000
# GET clock → status: advancing | ready; DELETE removes all attached objects
```

Limits: ≤3 customers/clock, ≤3 subs/customer, advance ≤2 billing periods per call;
clocks auto-delete after 30 days. Dashboard equivalent: Subscriptions → "Run simulation".

Use test clocks to exercise: trial→active conversion, renewal invoices, dunning
(`past_due` after a failing card), cancellation at period end, upgrades mid-cycle
(proration invoices).

## Debugging quick hits

- **Webhook signature failures**: body was parsed/re-serialized before
  verification, or you're mixing the `stripe listen` secret with the Dashboard
  endpoint secret (they differ).
- **Fulfillment on redirect success URL only**: users close tabs — always fulfill
  from `checkout.session.completed` server-side.
- **Double fulfillment**: both `checkout.session.completed` and `invoice.paid`
  grant the first period — make provisioning idempotent per subscription+period.
- **SCA-incomplete subs**: `incomplete` subs are not paid; watch
  `invoice.payment_action_required` and surface authentication.
- **Live vs test mixups**: objects (customers, prices) exist per mode; a
  `price_xxx` from test mode 404s with live keys.
- Search account activity fast: Dashboard → Developers → Events / Logs, or the
  Stripe MCP (`stripe_api_read`, `search_stripe_resources`).
