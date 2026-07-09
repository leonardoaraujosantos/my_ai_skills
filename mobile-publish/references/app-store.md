# App Store Publishing (verified July 2026)

## Versioning

Two build settings (Info.plist references them via `$(…)`):
- `MARKETING_VERSION` → `CFBundleShortVersionString` (user-facing, `1.4.2`)
- `CURRENT_PROJECT_VERSION` → `CFBundleVersion` (build number)

```bash
# Requires VERSIONING_SYSTEM = apple-generic; run beside the .xcodeproj
agvtool what-version
agvtool next-version -all              # bump build number everywhere
agvtool new-version -all 42
agvtool new-marketing-version 1.4.2
# CI alternative: xcodebuild … CURRENT_PROJECT_VERSION=$CI_BUILD_NUMBER
```

Rules: `CFBundleVersion` must be **unique within a marketing version**
(reuse across versions is fine), monotonically increasing within a version
train, format `[0-9]+(.[0-9]+)*` (≤3 parts, ≤18 chars each). TestFlight builds
expire after **90 days**.

## Upload paths (preference order for automation)

1. **App Store Connect API build-upload endpoints** (WWDC 2025) — pure REST, no
   macOS/Xcode dependency: `POST /v1/buildUploads` → create `buildUploadFiles`
   → `PUT` binary parts → confirm. Pairs with ASC **webhooks** (processing
   complete) and the TestFlight Feedback API. The strategic direction.
2. **fastlane**: `pilot` (upload + tester mgmt), `deliver` (metadata/
   screenshots/submission). Auth with an ASC API key (`ASC_KEY_*` env vars) —
   never Apple ID + 2FA sessions in CI. With API-key auth add
   `--precheck_include_in_app_purchases false` to deliver.
3. **altool** — soft-deprecated but working:
   ```bash
   # key at ~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8
   xcrun altool --validate-app -f MyApp.ipa -t ios --apiKey <KEY_ID> --apiIssuer <ISSUER>
   xcrun altool --upload-app   -f MyApp.ipa -t ios --apiKey <KEY_ID> --apiIssuer <ISSUER>
   ```
4. Skip the .ipa entirely: `-exportArchive` with `destination: upload` in
   ExportOptions.plist (see xcode-tools).
5. Manual: Transporter.app, Xcode Organizer.

Note: altool's *notarization* role is dead (that's `notarytool`, macOS-only
concern) — a different deprecation people conflate with app upload.

## TestFlight

| | Internal | External |
|---|----------|----------|
| Who | ≤100 ASC team members (30 devices each) | ≤10,000 via email/public link |
| Review | None — available after processing | Beta App Review on first build per version (<24–48 h typical) |
| Automation | safe default target | needs beta test info (contact email, what-to-test) |

Processing after upload: typically 5–60 min. **Blockers**: "Missing Compliance"
(set `ITSAppUsesNonExemptEncryption = NO` in Info.plist for exempt-only crypto);
invalid entitlements caught in processing (build silently disappears + email);
missing beta test info for external groups; 90-day expiry.

## Submission checklist

- **Screenshots**: PNG/JPEG, RGB, no alpha, exact sizes, 1–10 per class.
  Required: iPhone 6.9" **1320×2868** (or landscape swap); iPad 13"
  **2064×2752** (or 2048×2732). Apple scales smaller devices from the largest —
  one iPhone set + one iPad set suffices. Clean status bar first (see
  ios-simulator `status_bar override`).
- **Privacy nutrition labels**: declare everything your SDKs collect too —
  mismatch is a 5.1.1/5.1.2 rejection vector.
- **Age rating**: 2026 system is 4+/9+/13+/16+/18+ with the expanded
  questionnaire (mandatory since Jan 31 2026 — un-answered apps can't submit
  updates).
- **Review notes**: working demo account credentials for any gated
  functionality (dead demo login is a top 2.1 rejection), hardware/setup notes.
- Also: privacy policy URL, support URL, description/keywords, pricing, content
  rights.

## Review rejections (indie frequency leaders) and responses

| Guideline | What it is | Response |
|-----------|-----------|----------|
| 4.3 Spam (~28%) | Template/AI-generated look-alikes; June 2026 wording: "indistinguishable from what's already widely available" | Differentiate genuinely before resubmitting |
| 2.1 Completeness (~22%) | Crash on launch (reviewer runs IPv6/NAT64), broken features, dead demo login, placeholder content, "beta" labels | Fix, test on clean device + IPv6 network, explain the fix in Resolution Center |
| 4.2 Minimum functionality | Thin website wrappers | Add native value (offline, notifications, widgets) and argue it concretely |
| 3.1.1 In-App Purchase | Digital goods outside IAP; external purchase links without entitlement (US external-link entitlement / EU DMA terms are the exceptions) | Remove/gate the flow or adopt the proper entitlement — see the payments skill |
| 5.1.1 Privacy | Permission prompts without purpose strings, forced registration, label mismatches | Precise `NS*UsageDescription` strings, optional login, align labels |

Process: reply in **Resolution Center** first (ask for specifics if vague);
escalate to the App Review Board appeal only for misapplied guidelines.
Repeated identical resubmissions risk delayed reviews.

## fastlane quick reference

Maintained by the Mobile Native Foundation (transferred Oct 2023; release
cadence revived late 2025). Roles: **match** (encrypted shared certs/profiles
in git/S3/GCS), **gym** (`build_app`), **pilot** (`upload_to_testflight`),
**deliver** (`upload_to_app_store`).
