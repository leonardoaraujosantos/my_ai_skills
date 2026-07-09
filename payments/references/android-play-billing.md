# Android — Google Play Billing Testing & Debugging Playbook

Scope: one-time products and subscriptions via Play Billing Library + Google Play
Developer API + Real-Time Developer Notifications (RTDN).

Current library: `com.android.billingclient:billing:9.1.0` (+ `billing-ktx`).
**Deadline: all new apps/updates must use Billing Library 8+ by 2026-08-31.**
v8 renamed "in-app items" → "one-time products" and added
`enableAutoServiceReconnection()`; v9 added Billing Choice APIs.

## Core client flow (v8+ idioms)

1. Build one client per app:
   ```kotlin
   BillingClient.newBuilder(context)
     .setListener(purchasesUpdatedListener)
     .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
     .enableAutoServiceReconnection()   // makes onBillingServiceDisconnected a no-op
     .build()
   ```
2. `startConnection(...)` → wait for `onBillingSetupFinished` with `OK`.
3. `queryProductDetailsAsync(...)` — v8 result carries `productDetailsList` **and**
   `unfetchedProductList` (per-product failure codes — check it).
4. `launchBillingFlow(activity, params)` — each `ProductDetailsParams` needs
   `setProductDetails()` + `setOfferToken()` (from `subscriptionOfferDetails` /
   `oneTimePurchaseOfferDetailsList`). Set `setIsOfferPersonalized(true)` for EU;
   `setObfuscatedAccountId()` for fraud detection and user mapping.
5. Handle `PurchasesUpdatedListener.onPurchasesUpdated(...)`.
6. **Acknowledge or consume within 3 days** (see trap below).
7. `queryPurchasesAsync(...)` in `onBillingSetupFinished` **and every `onResume()`**
   — catches purchases from other devices, promo redemptions, missed callbacks.
   On-hold/paused subs only appear with `includeSuspendedSubscriptions` (v8.1+).

## THE trap: the 3-day acknowledgment window

Every purchase reaching `PURCHASED` state must be acknowledged
(`acknowledgePurchase` for subs/non-consumables, `consumeAsync` for consumables —
consume implies ack; backend: `purchases.products:acknowledge`/`:consume`) within
**3 days**, or Google **auto-refunds and revokes** it. Symptoms: refunds in the
Orders report with no user action.

- Never acknowledge a `PENDING` purchase — the clock starts at `PENDING→PURCHASED`.
- Guard: `purchase.purchaseState == PURCHASED && !purchase.isAcknowledged()`.
- Renewals don't need ack — only initial purchases and each **new token**
  (upgrade/downgrade/resubscribe).
- For license testers the window shrinks to minutes (test purchases refund after
  ~3 min unacknowledged) — the fastest way to catch this bug pre-production.

## Testing

**License testers** (Play Console → account-level Settings → License testing):
no real charges, can sideload debug builds (package name must match a Play app
with ≥1 build ever uploaded), and get test instruments:
"always approves", "always declines", and **slow cards** that approve/decline
after a few minutes (essential for testing `PENDING` flows).

Accelerated renewals for license testers (max **6 renewals**, then expires):

| Real period | Test renewal |
|-------------|--------------|
| 1 week | 5 min |
| 1 month | 5 min |
| 3 months | 10 min |
| 6 months | 15 min |
| 1 year | 30 min |

Time-compressed lifecycle: trial 3 min; grace period 5 min; account hold 10 min;
pause 1/2/3 months → 5/10/15 min; ack window ≈3–5 min.

Other testing notes:
- **Internal testing track**: testers must opt in via the tester link;
  non-license-testers pay real money; per-user daily spend limits apply to
  draft/internal apps.
- **Play Billing Lab** app (`com.google.android.apps.play.billingtestcompanion`):
  change Play country, re-test trials/intro offers on the same account, force
  grace-period/account-hold transitions, test price changes. Configs expire after 2 h.
- Emulators need **Google Play** images (not just Google APIs) with a signed-in
  account and updated Play Store.

## RTDN (Real-Time Developer Notifications) via Cloud Pub/Sub

Setup: create Pub/Sub topic → grant Publisher to
`google-play-developer-notifications@system.gserviceaccount.com` → set the topic
in Play Console → Monetization setup → send a test notification.

Payload: Pub/Sub envelope, base64 `data` = `DeveloperNotification` with exactly
one of `subscriptionNotification`, `oneTimeProductNotification`,
`voidedPurchaseNotification`, `testNotification`. Notifications carry **only a
purchaseToken** — always call the Developer API for state. Dedup by Pub/Sub
`messageId`; delivery is at-least-once, unordered.

`subscriptionNotification.notificationType`:

| Value | Type | | Value | Type |
|-------|------|-|-------|------|
| 1 | SUBSCRIPTION_RECOVERED | | 10 | SUBSCRIPTION_PAUSED |
| 2 | SUBSCRIPTION_RENEWED | | 11 | SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED |
| 3 | SUBSCRIPTION_CANCELED | | 12 | SUBSCRIPTION_REVOKED |
| 4 | SUBSCRIPTION_PURCHASED | | 13 | SUBSCRIPTION_EXPIRED |
| 5 | SUBSCRIPTION_ON_HOLD | | 17 | SUBSCRIPTION_ITEMS_CHANGED |
| 6 | SUBSCRIPTION_IN_GRACE_PERIOD | | 18 | SUBSCRIPTION_CANCELLATION_SCHEDULED |
| 7 | SUBSCRIPTION_RESTARTED | | 19 | SUBSCRIPTION_PRICE_CHANGE_UPDATED |
| 9 | SUBSCRIPTION_DEFERRED | | 20 | SUBSCRIPTION_PENDING_PURCHASE_CANCELED |

One-time: `ONE_TIME_PRODUCT_PURCHASED=1`, `ONE_TIME_PRODUCT_CANCELED=2`.
Voided: productType 1=sub / 2=one-time; refundType 1=full / 2=partial.

## Server-side verification (Google Play Developer API)

- Subscriptions: `GET .../androidpublisher/v3/applications/{pkg}/purchases/subscriptionsv2/tokens/{token}`
  (v1 `purchases.subscriptions.get` is deprecated). One-time:
  `purchases.products.get`. Scope: `https://www.googleapis.com/auth/androidpublisher`.
- **Service account setup**: create SA in GCP → enable the Google Play Android
  Developer API in that project → invite the SA email in Play Console (Users and
  permissions) with financial-data + order-management permissions.
  Gotcha: fresh SAs can 401 for **24–36 h**; editing any product in Play Console
  historically forces a refresh.
- `SubscriptionPurchaseV2` key fields: `subscriptionState`
  (ACTIVE/CANCELED/IN_GRACE_PERIOD/ON_HOLD/PAUSED/EXPIRED/PENDING),
  `acknowledgementState`, `lineItems[]` (productId, expiryTime, autoRenewingPlan
  vs prepaidPlan, offerDetails), `linkedPurchaseToken`, `testPurchase` (present
  only for license-tester purchases — use it to segregate test data).
- **linkedPurchaseToken rule**: upgrade/downgrade/resubscribe-before-expiry issues
  a NEW token whose `linkedPurchaseToken` points at the old one — invalidate the
  old token server-side or you will **double-grant entitlements**.
- Tokens stay queryable until **60 days after expiry**.
- Related: `subscriptionsv2.cancel`, `subscriptionsv2.revoke`,
  `purchases.voidedpurchases.list`.

## BillingResponseCode table

| Constant | Value | Fix |
|----------|-------|-----|
| SERVICE_DISCONNECTED | -1 | Use `enableAutoServiceReconnection()` (v8+) or retry `startConnection` |
| FEATURE_NOT_SUPPORTED | -2 | Check `isFeatureSupported()` first |
| OK | 0 | — |
| USER_CANCELED | 1 | User backed out of the sheet |
| SERVICE_UNAVAILABLE | 2 | Transient; exponential backoff |
| BILLING_UNAVAILABLE | 3 | Play Store outdated / no account / unsupported country / enterprise policy — usually not your bug |
| ITEM_UNAVAILABLE | 4 | Product inactive, wrong region, or wrong app |
| DEVELOPER_ERROR | 5 | API misuse or **signing mismatch** (debug build signed differently than uploaded) |
| ERROR | 6 | Fatal internal; backoff |
| ITEM_ALREADY_OWNED | 7 | Reconcile with `queryPurchasesAsync` — usually an unconsumed consumable |
| ITEM_NOT_OWNED | 8 | Consuming/acking something not owned — reconcile cache |
| NETWORK_ERROR | 12 | Backoff and retry |

## "Item not available for purchase" checklist

1. App never uploaded to any track with `com.android.vending.BILLING` — products
   can't even be created/activated until an AAB is uploaded (internal track is enough).
2. Product not activated in Play Console.
3. Tester not opted into the testing track (via the opt-in link) or not a license
   tester with a sideloaded build.
4. Product created minutes ago — propagation can take hours.
5. Installed build's `versionCode` lower than the uploaded one.
6. Signing mismatch → shows as DEVELOPER_ERROR instead.

## Subscription lifecycle & entitlement

| State | Access? | Notes |
|-------|---------|-------|
| ACTIVE | Yes | |
| CANCELED | Yes until `expiryTime` | Resubscribe in Play before expiry → same token, `SUBSCRIPTION_RESTARTED` |
| IN_GRACE_PERIOD | Yes | Payment declined; expiryTime keeps extending; even "0 days" grace yields a silent ~24 h retry |
| ON_HOLD | **No** | Grace exhausted; not in `queryPurchasesAsync` by default; recovery resets billing date → `SUBSCRIPTION_RECOVERED` |
| PAUSED | **No** | User-initiated (1–3 months; not for annual); resume → RECOVERED or ON_HOLD |
| EXPIRED | No | Token queryable 60 more days |
| REVOKED (event) | Revoke immediately | Refund/chargeback |

Grace period and account hold are enabled by default for all auto-renewing base
plans. After full expiry, resubscribe creates a fresh token with
`outOfAppPurchaseContext.expiredPurchaseToken` (not `linkedPurchaseToken`).

## Ecosystem note

There is **no official Play Console MCP server** (community ones wrap the
androidpublisher API with a service-account key). Google's official Developer
Knowledge API/MCP is docs-retrieval only. Automation surface: androidpublisher
v3, Play Developer Reporting API, fastlane `supply`.
