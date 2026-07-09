---
name: mobile-publish
description: Publish native mobile apps to the App Store and Google Play - versioning discipline, archive/AAB signing, upload paths (App Store Connect API/altool/fastlane pilot, Play Developer API/fastlane supply), TestFlight and Play-track promotion, staged rollouts, store screenshot specs, privacy/data-safety forms, and review-rejection playbooks. Use when the user says "publish/release this app", "upload to TestFlight/App Store/Play Store", "promote to production", "staged rollout", "why was my app rejected", "store screenshots specs", or "bump the version/build number".
argument-hint: [ios|android] [step]
---

# Mobile Publish Skill

Store publishing playbooks, verified July 2026:

- `references/app-store.md` — versioning (agvtool), upload paths, TestFlight,
  screenshot specs, privacy labels, review rejections
- `references/play-store.md` — AAB/Play App Signing, versionCode, tracks &
  staged rollout, Play Developer API/fastlane supply, data safety, target API

Read the reference for the platform in play. Store rules and API-level
requirements change several times a year — for anything deadline- or
policy-sensitive, re-verify against the official docs before advising.

## Release pipeline shape (both stores)

```
bump version → build signed artifact → upload to store → internal testing
→ (beta review) wider testing → submit/promote → staged rollout → monitor
```

## Quick commands

| Step | iOS | Android |
|------|-----|---------|
| Bump build number | `agvtool next-version -all` | bump `versionCode` (must strictly increase, max 2100000000) |
| Build release artifact | `xcodebuild archive` + `-exportArchive` (see xcode-tools) | `./gradlew bundleRelease` → `app/build/outputs/bundle/release/*.aab` |
| Upload (CLI) | `xcrun altool --upload-app -f MyApp.ipa -t ios --apiKey <ID> --apiIssuer <UUID>` (or exportOptions `destination: upload`) | `fastlane supply --aab app.aab --track internal --json_key sa.json` |
| Validate before upload | `xcrun altool --validate-app -f MyApp.ipa -t ios --apiKey … --apiIssuer …` | `bundletool build-apks --bundle=app.aab --output=app.apks --local-testing` + `install-apks` |
| First testing tier | TestFlight internal (≤100 team members, no beta review) | Internal testing track (≤100 testers, near-instant) |
| Promote | External TestFlight (beta review) → App Store submission | Promote release between tracks (reuses reviewed artifact) |
| Gradual release | Phased release (7-day automatic) | Staged rollout percentage (manual bumps, can halt/resume) |

## Golden rules

1. **Never submit or promote to a public track/production without explicit user
   confirmation** — releases are customer-visible and reviews take days to redo.
   Uploading to TestFlight-internal or the Play internal track is the safe
   default scope for automation.
2. **Version discipline first**: a rejected/duplicate build number costs a full
   build-upload cycle. iOS: `CFBundleVersion` unique per marketing version.
   Android: `versionCode` strictly increasing across ALL tracks.
3. **Answer export compliance in the project, not the UI**: set
   `ITSAppUsesNonExemptEncryption` in Info.plist (NO if you only use
   HTTPS/exempt crypto) or every TestFlight build blocks on "Missing Compliance".
4. **Keep signing assets out of repos**: `.p8` ASC keys, `.p12` certs, Android
   keystores, and Play service-account JSON live in CI secrets / keychains.
   Losing the Android **upload key** is recoverable (reset request, ~48 h);
   losing a pre-Play-App-Signing **app signing key** is not.
5. **Store metadata is code**: keep screenshots, descriptions, and release notes
   in-repo (fastlane `deliver`/`supply` layouts) so releases are reproducible.
6. Fastlane is community-maintained under the Mobile Native Foundation (releases
   active again since late 2025) — stable, but pin versions in `Gemfile.lock`.
