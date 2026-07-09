# Cross-Platform Subscription Architecture

For apps selling the same product/subscription on Web (Stripe), iOS (App Store),
and Android (Google Play). Read this when designing the backend or debugging
entitlement drift between platforms.

## The canonical backend shape

```
Stripe webhooks ──────┐
App Store Server      ├──► verify signature ─► dedupe by event ID ─► normalize
Notifications V2 ─────┤        to a common lifecycle event ─► update entitlements
Play RTDN (Pub/Sub) ──┘        table ─► (async) side effects (email, analytics)

Clients (web/iOS/Android) ──► GET /me/entitlements   (server is source of truth)
```

Rules:
- One **entitlements table** keyed by your internal user ID, with per-row:
  `platform`, `product_id`, `status`, `expires_at`, `original_transaction_id` /
  `purchase_token` / `subscription_id`, `environment` (prod/sandbox/test).
- Store the **raw platform payload** alongside the normalized row — you will need
  it for disputes and debugging.
- Apple/Google notifications carry only IDs/tokens → always re-fetch state from
  the App Store Server API / `purchases.subscriptionsv2.get` before updating.
- Keep sandbox/test events out of production entitlements: check
  `data.environment == "Sandbox"` (Apple), `testPurchase` presence (Google),
  `livemode == false` (Stripe).

## User identity mapping (the #1 cross-platform bug source)

| Platform | Field to carry your user ID |
|----------|------------------------------|
| Stripe | `client_reference_id` on Checkout Session + `metadata` on customer/subscription |
| iOS | `appAccountToken` (UUID set at purchase; echoed in every transaction/notification) |
| Android | `setObfuscatedAccountId()` at `launchBillingFlow` + your own token↔user table |

Without these, server notifications arrive for purchases you can't attribute.
Handle the "purchase before login" and "restore on second device" cases explicitly:
iOS restores via `Transaction.currentEntitlements`, Android via
`queryPurchasesAsync`, Stripe via customer email/portal login.

## Unified lifecycle event mapping

| Lifecycle event | Stripe | Apple (ASSN V2) | Google (RTDN) |
|-----------------|--------|-----------------|----------------|
| Initial purchase | `checkout.session.completed` + `customer.subscription.created` | `SUBSCRIBED / INITIAL_BUY` | `SUBSCRIPTION_PURCHASED` (4) |
| Renewal succeeded | `invoice.paid` | `DID_RENEW` | `SUBSCRIPTION_RENEWED` (2) |
| Payment failed → retrying | `invoice.payment_failed` (status `past_due`) | `DID_FAIL_TO_RENEW` | `SUBSCRIPTION_IN_GRACE_PERIOD` (6) |
| Grace period ended, still retrying | (dunning settings) | `GRACE_PERIOD_EXPIRED` | `SUBSCRIPTION_ON_HOLD` (5) |
| Recovered from billing failure | `invoice.paid` after retries | `DID_RENEW / BILLING_RECOVERY` | `SUBSCRIPTION_RECOVERED` (1) |
| User canceled (access until period end) | `customer.subscription.updated` (`cancel_at_period_end=true`) | `DID_CHANGE_RENEWAL_STATUS / AUTO_RENEW_DISABLED` | `SUBSCRIPTION_CANCELED` (3) |
| Fully expired | `customer.subscription.deleted` | `EXPIRED` (+subtype) | `SUBSCRIPTION_EXPIRED` (13) |
| Resubscribed | new subscription / `resumed` | `SUBSCRIBED / RESUBSCRIBE` | `SUBSCRIPTION_RESTARTED` (7) |
| Upgrade/downgrade | `customer.subscription.updated` (proration invoice) | `DID_CHANGE_RENEWAL_PREF / UPGRADE|DOWNGRADE` | `SUBSCRIPTION_ITEMS_CHANGED` (17) + **new token, invalidate `linkedPurchaseToken`** |
| Paused | `customer.subscription.paused` | (n/a) | `SUBSCRIPTION_PAUSED` (10) |
| Refund / revoke | `charge.refunded`, `charge.dispute.created` | `REFUND`, `REVOKE`, `REFUND_REVERSED` | `SUBSCRIPTION_REVOKED` (12), voided purchases |
| One-time purchase | `checkout.session.completed` (`mode=payment`) | `ONE_TIME_CHARGE` | `ONE_TIME_PRODUCT_PURCHASED` |

Entitlement rule of thumb: grant during `active/trialing`, `subscribed/inGracePeriod`,
`ACTIVE/CANCELED-until-expiry/IN_GRACE_PERIOD`; revoke on hold, pause, expiry, and
revocation. Grace period keeps access; account hold does not.

## Local development for server notifications

Stripe has `stripe listen`; Apple and Google POST to public HTTPS endpoints, so:
- Tunnel: `ngrok http 8080` / `cloudflared tunnel --url http://localhost:8080`,
  set the tunnel URL as the sandbox notification URL (Apple: separate sandbox URL
  in ASC; Google: Pub/Sub **push** subscription to the tunnel, or a **pull**
  subscription drained by a local script).
- Verify wiring end-to-end before debugging logic: Apple **Request a Test
  Notification** endpoint (then Get Test Notification Status); Google Play
  Console → Monetization setup → "Send test notification"
  (`testNotification` payload); Stripe `stripe trigger <event>`.
- Replay/backfill: Apple Get Notification History (180 d prod / 30 d sandbox);
  Stripe Dashboard event resend; Google has no replay — reconcile by calling
  `subscriptionsv2.get` on stored tokens (voided purchases via
  `purchases.voidedpurchases.list`).

## Accelerated-time testing comparison

| | Stripe | iOS sandbox | Android license tester | Xcode local |
|---|--------|-------------|------------------------|-------------|
| Mechanism | Test clocks (API/Dashboard) | Renewal-rate setting per sandbox account | Automatic for license testers | `.storekit` renewal rate / `SKTestSession.timeRate` |
| 1 month renews in | you choose (advance calls) | 5 min (default) | 5 min | down to 30 s |
| Max renewals | 2 periods per advance | 12 | 6 | unlimited |
| Can force failure | failing test card on customer | billing-retry toggle on device/ASC | "always declines" / slow-decline card | `failTransactionsEnabled`, simulated errors |

## Reconciliation job (recommended)

Notifications get missed (endpoint down, Pub/Sub misconfig, deploy windows). Run a
daily job that re-fetches state for every entitlement expiring within N days:
Stripe `subscriptions.list`, Apple Get All Subscription Statuses, Google
`subscriptionsv2.get` — and diffs against the entitlements table. This converts
"silent entitlement drift" into a monitored metric.

## Platform-fee / routing note

Digital goods **must** use IAP on iOS/Android store builds (with regional
exceptions and external-purchase-link programs that change frequently — verify
current rules before advising). Physical goods/services must NOT use IAP — use
Stripe in-app. Web checkout via Stripe for the same subscription is standard;
just ensure one active subscription per user across platforms: check the
entitlements table before starting a new checkout and surface "you already have
an active subscription on <platform>" (upgrades must happen on the owning platform).
