---
name: payments
description: Cross-platform payment and subscription development/debugging playbooks for Stripe (web), Apple StoreKit 2 / App Store Connect (iOS), and Google Play Billing (Android). Covers webhook and server-notification testing, sandbox/test-mode workflows, accelerated subscription renewals, entitlement architecture, and failure decision trees. Use when the user says "debug this payment/purchase", "test my subscription flow", "webhooks aren't arriving", "products not loading", "IAP sandbox", "stripe test/trigger/test clock", "RTDN", "App Store Server Notifications", or "why was this purchase refunded".
argument-hint: [stripe|ios|android|architecture] [topic]
---

# Payments Skill

Development and debugging playbooks for the three payment stacks:

| Platform | Stack | Reference file |
|----------|-------|----------------|
| Web | Stripe (Checkout, Payment Intents, Billing) | `references/stripe.md` |
| iOS / iPadOS / macOS | StoreKit 2, App Store Connect, App Store Server API | `references/ios-storekit.md` |
| Android | Play Billing Library 8/9, Play Developer API, RTDN | `references/android-play-billing.md` |
| All | Unified entitlement backend, event mapping, identity | `references/architecture.md` |

**How to use this skill:** identify the platform(s) involved, then read the matching
reference file(s) before answering. For any app that sells the same subscription on
more than one platform, also read `references/architecture.md` — it maps the three
event vocabularies onto one lifecycle and defines the server-side source-of-truth
pattern.

Facts in the reference files were verified July 2026. For anything
version-sensitive (SDK APIs, current library versions, new endpoint shapes), confirm
against live docs: use the **context7 MCP** or `search_stripe_documentation` on the
Stripe MCP rather than trusting memory.

---

## Golden rules (all platforms)

1. **The server is the source of truth for entitlements.** Client-side purchase
   results unlock optimistically at most; real access comes from a server-side
   entitlements record updated by verified server events.
2. **Notifications are triggers, not truth.** Play RTDN and App Store Server
   Notifications carry only tokens/IDs — always call the platform API
   (`purchases.subscriptionsv2.get`, App Store Server API) to fetch actual state.
   Stripe webhooks carry full objects but can arrive out of order — re-fetch when
   ordering matters.
3. **Handlers must be idempotent.** All three platforms deliver at-least-once and
   unordered. Deduplicate by event ID (`event.id` / `notificationUUID` /
   Pub/Sub `messageId`) and make state transitions replay-safe.
4. **Verify signatures on the raw body.** Stripe: `constructEvent` with the raw
   request body. Apple: verify the JWS `x5c` chain to the Apple Root CA
   (use `app-store-server-library`). Google: validate the Pub/Sub push
   authentication (OIDC token) on the endpoint.
5. **Acknowledge/finish every purchase.** Android: unacknowledged purchases are
   auto-refunded after 3 days (≈3–5 minutes for license testers). iOS: always call
   `transaction.finish()` after granting content. Stripe: fulfill on
   `checkout.session.completed` + `invoice.paid`, never on client redirect alone.
6. **Test-mode artifacts never validate in production.** Stripe test keys, Xcode
   StoreKit local certificates, and sandbox receipts/tokens all fail against
   production endpoints — environment mixups are a top-3 support issue on every
   platform.

---

## Fast triage — where to start

| Symptom | Likely platform doc + section |
|---------|------------------------------|
| Webhook endpoint never fires locally | `stripe.md` → CLI `stripe listen`; `architecture.md` → tunneling for RTDN/ASSN |
| Products load as empty array (iOS) | `ios-storekit.md` → "Products not loading" decision tree (agreements/tax/banking first) |
| "Item not available for purchase" (Android) | `android-play-billing.md` → availability checklist (track upload, license tester opt-in, propagation) |
| Purchases mysteriously refunded (Android) | `android-play-billing.md` → 3-day acknowledgment window |
| Need to test a year of renewals in minutes | `stripe.md` → test clocks; `ios-storekit.md` → sandbox renewal-rate tables; `android-play-billing.md` → license-tester renewal table |
| Payment failure / dunning / grace period flows | platform doc → lifecycle section; compare in `architecture.md` mapping table |
| Refund/chargeback handling | platform doc → REFUND / SUBSCRIPTION_REVOKED / charge.dispute events |
| Same sub bought on two platforms double-granting | `architecture.md` → identity + linkedPurchaseToken rules |

---

## Environment setup

### Stripe tooling (recommended, complements this skill)

- **Official Stripe skills plugin** (kept current by Stripe):
  `claude plugin install stripe@claude-plugins-official`
  — ships `stripe-best-practices` (+ Connect/Tax/Treasury references) and
  `upgrade-stripe`. This skill defers to it for greenfield integration design;
  our `stripe.md` focuses on **testing and debugging** workflows.
- **Stripe MCP** (live account access — read/write API, docs search):
  `claude mcp add --transport http stripe https://mcp.stripe.com/`
  (OAuth; or local `npx -y @stripe/mcp --tools=all --api-key=$STRIPE_TEST_KEY`).
  Prefer **restricted keys** (`rk_`) and **test mode** keys for agent use.
- **Stripe CLI**: `brew install stripe/stripe-cli/stripe` (or `npm i -g @stripe/cli`),
  then `stripe login`. No account? `stripe sandbox create` mints working test keys.

### Apple tooling

- Xcode with a `.storekit` configuration file per scheme for offline testing;
  `StoreKitTest` framework for CI (see `ios-storekit.md`).
- App Store Connect API key (`.p8` + key ID + issuer ID) for ASC/Server API work —
  keep under `~/.appstoreconnect/`, never in a repo.

### Google tooling

- Play Console with **license testers** configured (Settings → License testing).
- A GCP service account with the Android Publisher API enabled and Play Console
  permissions for server-side verification (see `android-play-billing.md` for the
  24–36h propagation gotcha).

---

## Safety

- **Never run write operations against live/production payment accounts without
  explicit user confirmation** — refunds, product/price changes, subscription
  cancellations, and price schedules are customer-visible and often irreversible.
  Default every Stripe MCP/API example to test mode (`sk_test_`/`rk_test_` or a
  sandbox), and every ASC/Play write to a dry-run + confirm step.
- Never commit or echo secret keys, `.p8` files, or service-account JSON. When a
  command needs one, reference an env var.
