# iOS — StoreKit 2 / App Store Connect Testing & Debugging Playbook

Scope: in-app purchases and auto-renewable subscriptions on Apple platforms.
Modern stack = StoreKit 2 (JWS transactions) + App Store Server API + App Store
Server Notifications V2. `verifyReceipt` is legacy/deprecated.

## Three test environments (increasing realism)

| Environment | Needs ASC? | Network? | Best for |
|-------------|-----------|----------|----------|
| StoreKit Testing in Xcode (`.storekit` file) | No | No | Day-to-day dev, CI, edge cases (refunds, Ask to Buy, interrupted purchases) |
| Sandbox (Sandbox Apple Accounts) | Yes | Yes | Real ASC product data, server notification testing, renewal flows |
| TestFlight (always sandbox env) | Yes | Yes | Production-like distribution testing |

## StoreKit Testing in Xcode

- Create: File → New → File from Template → **StoreKit Configuration File**. Two
  kinds: **local** (hand-edited, never uploads) and **synced** (pulls from ASC,
  read-only until Editor → Convert to Local StoreKit Configuration).
- Enable per scheme: Edit Scheme → Run → Options → StoreKit Configuration (one
  active file per scheme; the choice is recorded in the `.xcscheme`).
- Editor menu toggles: Interrupted Purchases, Billing Grace Period, Billing Retry
  on Renewal, **Subscription Renewal Rate** (e.g. monthly renews every 30 s), Save
  Public Certificate.
- Runtime control: **Debug → StoreKit → Manage Transactions** — delete
  transactions (resets intro-offer eligibility), resolve interrupted purchases,
  refund, request price-increase consent.
- Local receipts are signed by a **local test root certificate** — they always fail
  production validation. Pattern:

```swift
#if DEBUG
let certificate = "StoreKitTestCertificate"
#else
let certificate = "AppleIncRootCertificate"
#endif
```

## StoreKitTest framework (automation / CI)

`import StoreKitTest` (Xcode 12+). `SKTestSession` drives a single shared test
environment — run environment-mutating tests **serially**.

```swift
let session = try SKTestSession(configurationFileNamed: "Products")
session.resetToDefaultState()
session.disableDialogs = true            // essential for CI
session.clearTransactions()
```

Key API by scenario:

| Scenario | API |
|----------|-----|
| Out-of-app purchase | `buyProduct(productIdentifier:)` |
| Refund / revoke | `refundTransaction(identifier:)` |
| Force failures | `failTransactionsEnabled`, `setSimulatedError(_:forAPI:)` (per-API: LoadProducts, Purchase, SubscriptionStatus, RefundRequest, OfferCodeRedeem…) |
| Time compression | `timeRate` (`SKTestSession.TimeRate`) |
| Expire / renew now | `expireSubscription(productIdentifier:)`, `forceRenewalOfSubscription(productIdentifier:)` |
| Auto-renew toggle | `enable/disableAutoRenewForTransaction(identifier:)` |
| Billing retry & grace | `shouldEnterBillingRetryOnRenewal`, `billingGracePeriodIsEnabled`, `resolveIssueForTransaction(identifier:)` |
| Ask to Buy | `askToBuyEnabled`, `approve/declineAskToBuyTransaction(identifier:)` |
| Price increase consent | `requestPriceIncreaseConsentForTransaction(identifier:)`, `consentTo…`, `decline…` |
| Storefront / locale | `storefront`, `locale` |

CI invocation is plain `xcodebuild test -scheme <S> -destination 'platform=iOS
Simulator,name=iPhone 16'` — there is no `-storeKitConfiguration` flag; the config
comes from the scheme or from `SKTestSession(configurationFileNamed:)` directly.

## Sandbox testing

Prereqs (each one blocks product loading if missing):
1. Active Developer Program membership.
2. **Paid Applications Agreement signed by the Account Holder** + banking/tax
   "Clear"/"Active" (ASC → Business).
3. Products configured in ASC (must reach "Ready to Submit" to be fetchable).
4. Sandbox accounts created in ASC → Users and Access → Sandbox.

Workflow:
- Dev-signed builds: no sign-out needed; the sandbox account appears under
  **Settings → Developer** after the first purchase attempt. `[Environment: Sandbox]`
  on the sign-in sheet confirms sandbox.
- TestFlight: to control sandbox settings you must sign out of Media & Purchases
  and sign in with the sandbox account (use a dedicated test device — signing out
  can drop access to real purchased content).
- **Clear Purchase History** (ASC or Settings → Developer): irreversible, restores
  intro-offer eligibility, takes minutes; sign out/in on device to flush cache.
  Also available programmatically via the ASC Sandbox Testers API.
- ASC product metadata changes take **up to 1 hour** to propagate to sandbox.

### Sandbox renewal-rate tables (per sandbox account; set in ASC or on-device)

Subscriptions auto-renew **up to 12 times**, then auto-renew turns off.

| Real duration | @3 min | @5 min (default) | @30 min | @1 hr |
|---------------|--------|------------------|---------|-------|
| 1 week | 3 min | 3 min | 10 min | 15 min |
| 1 month | 3 min | 5 min | 30 min | 1 hr |
| 2 months | 6 min | 10 min | 1 hr | 2 hr |
| 3 months | 9 min | 15 min | 1.5 hr | 3 hr |
| 6 months | 18 min | 30 min | 3 hr | 6 hr |
| 1 year | 36 min | 1 hr | 6 hr | 12 hr |

Billing retry: 6 / 10 / 60 / 15–60 min; grace period: 3 / 3–5 / 10–30 / 60–120 min
respectively. Accelerated subs can lapse before the renewal fires — handle it (it
happens in production too).

## Client-side entitlements (StoreKit 2)

`Transaction.currentEntitlements` emits the latest transaction per entitled
product: every non-consumable; latest auto-renewable whose state is `.subscribed`
or `.inGracePeriod`; latest non-renewing sub. **Excludes refunded/revoked products
and all consumables** (use `Transaction.unfinished` / `Transaction.all`). Always
switch on `.verified/.unverified` and call `transaction.finish()` after granting
content. Listen to `Transaction.updates` from app launch.

## App Store Server API (server-side truth)

- Base URLs: prod `https://api.storekit.apple.com/`, sandbox
  `https://api.storekit-sandbox.apple.com/` (path is case-sensitive).
- Environment probing: call production; on error `4040010`
  (TransactionIdNotFound) retry sandbox. App Review runs in sandbox, so your
  production server **must** handle sandbox-signed data.
- Auth: ES256 JWT from an ASC API key — header `{"alg":"ES256","kid":"<keyId>"}`,
  payload `{"iss":"<issuerId>","aud":"appstoreconnect-v1","iat","exp"}`, signed
  with the `.p8`; max lifetime **20 minutes**.
- All responses are **JWS-signed** (`JWSTransaction`, `JWSRenewalInfo`) — verify
  the `x5c` chain to the Apple Root CA. Don't hand-roll: use Apple's
  `app-store-server-library` (Swift/Java/Python/Node) — it provides the API
  client, `SignedDataVerifier` (`verifyAndDecodeTransaction/RenewalInfo/
  AppTransaction`), receipt→transactionId migration, and promotional-offer
  signature generation.
- Key endpoints: Get Transaction History, Get Transaction Info, Get All
  Subscription Statuses, Get Refund History, Send Consumption Information (reply
  to `CONSUMPTION_REQUEST`), Extend Renewal Date, Get Notification History
  (**180 d prod / 30 d sandbox**), **Request a Test Notification** (verify your
  endpoint wiring).

## App Store Server Notifications V2

HTTP POST of a `signedPayload` JWS → decode to `{notificationType, subtype,
notificationUUID, data|summary|externalPurchaseToken}`. Separate sandbox URL
configurable in ASC; `data.environment == "Sandbox"`.

| Type | Subtypes | Meaning |
|------|----------|---------|
| SUBSCRIBED | INITIAL_BUY, RESUBSCRIBE | New subscription / resubscribe |
| DID_RENEW | BILLING_RECOVERY | Successful renewal (recovery = exited billing retry) |
| DID_CHANGE_RENEWAL_PREF | UPGRADE, DOWNGRADE | Plan change in group (no subtype = downgrade canceled) |
| DID_CHANGE_RENEWAL_STATUS | AUTO_RENEW_ENABLED / _DISABLED | Auto-renew toggled (cancel = DISABLED) |
| DID_FAIL_TO_RENEW | GRACE_PERIOD | Billing failure → retry (60-day window) |
| GRACE_PERIOD_EXPIRED | — | Grace ended, retry continues, revoke access |
| EXPIRED | VOLUNTARY, BILLING_RETRY, PRICE_INCREASE, PRODUCT_NOT_FOR_SALE | Sub expired |
| OFFER_REDEEMED | UPGRADE, DOWNGRADE | Subscriber redeemed offer/win-back code |
| ONE_TIME_CHARGE | — | Consumable / non-consumable / non-renewing purchase |
| PRICE_INCREASE | PENDING, ACCEPTED | Price-increase consent flow |
| REFUND / REFUND_DECLINED / REFUND_REVERSED | — | Refunds (`revocationDate/Reason`); REVERSED → reinstate |
| CONSUMPTION_REQUEST | — | Reply via Send Consumption Information |
| RENEWAL_EXTENDED / RENEWAL_EXTENSION | SUMMARY, FAILURE | Renewal-date extensions |
| REVOKE | — | Family Sharing access lost — revoke now |
| TEST | — | From the Request a Test Notification endpoint |

Canonical mappings: billing retry entry = `DID_FAIL_TO_RENEW`; grace entry =
`DID_FAIL_TO_RENEW/GRACE_PERIOD`; recovery = `DID_RENEW/BILLING_RECOVERY`;
user cancel = `DID_CHANGE_RENEWAL_STATUS/AUTO_RENEW_DISABLED` (access continues
until expiry, then `EXPIRED/VOLUNTARY`).

## "Products not loading" decision tree (empty product array)

1. **Agreements/tax/banking** — Paid Applications Agreement signed and banking
   "Clear"? (Most common cause; also behind `SKErrorDomain Code=0 "Cannot connect
   to iTunes Store"`.)
2. **Bundle ID mismatch** between build and ASC app record (silent empty result).
3. **Product ID typo** between code and ASC.
4. **Product state** — `MISSING_METADATA` or removed-from-sale products don't
   fetch; subs need "Ready to Submit".
5. **Propagation delay** — up to 1 hour after ASC edits (longer for new apps).
6. Simulator without a `.storekit` config file selected in the scheme.

## Other common pain points

- **Sandbox password prompt shows the production account**: you're signed into
  the wrong session — check Settings → Developer, not Settings → [name].
- **Offer codes**: real codes don't work in sandbox; Xcode local testing needs
  the `.storekit` Offer Codes section + `presentCodeRedemptionSheet()`; the
  redemption sheet doesn't work on simulator.
- **Family Sharing**: enable per-product in ASC; test with Sandbox Test Families
  (ASC-only, organizer + 5, same storefront); revocation arrives as `REVOKE`;
  shared transactions have `ownershipType == .familyShared`.
- **21007 from verifyReceipt** (legacy): sandbox receipt sent to production —
  try prod, fall back to sandbox.
- Sandbox itself is occasionally slow/down; there's no status page — check the
  Apple developer forums before debugging your own code for hours.

## App Store Connect API (managing IAP products programmatically)

Same JWT auth as above against `https://api.appstoreconnect.apple.com`. Endpoint
families: `inAppPurchases` (v2) + localizations + price schedules + `pricePoints`
(`filter[territory]=USA`) + review screenshots; `subscriptionGroups` /
`subscriptions` + prices, intro/promotional offers, offer codes, availability;
Sandbox Testers (clear purchase history). Product state machine:
`MISSING_METADATA → READY_TO_SUBMIT`. Discipline for writes: **dry-run → show the
user → apply** — never apply a price/availability change the user hasn't seen.
