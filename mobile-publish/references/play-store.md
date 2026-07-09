# Google Play Publishing (verified July 2026)

## Build & signing

```bash
# One-time upload keystore
keytool -genkeypair -v -keystore upload-keystore.jks -alias upload \
  -keyalg RSA -keysize 2048 -validity 10000

./gradlew bundleRelease     # → app/build/outputs/bundle/release/app-release.aab
```

Gradle `signingConfigs` points at the **upload key**; keep secrets in
`keystore.properties`/CI env (see android-tools `references/gradle.md`).

**Play App Signing** (mandatory for apps created since Aug 2021): Google holds
the **app signing key** (what devices see); you hold only the **upload key**.
Lost/compromised upload key → Play Console → Setup → App signing → Request
upload key reset (new key valid in ~48 h; users unaffected).

Local AAB testing (AABs aren't directly installable):

```bash
bundletool build-apks --bundle=app.aab --output=app.apks --local-testing
bundletool install-apks --apks=app.apks
bundletool build-apks … --mode=universal    # single fat APK
```

## versionCode / versionName

`versionCode`: positive int, max **2100000000**, strictly increasing across
every uploaded artifact on all tracks. Strategies: CI build number; date-based
`yyMMddNN`; packed semver `major*10000 + minor*100 + patch`. `versionName`:
free-form user-facing string.

## Tracks, promotion, rollout

Ladder: **Internal testing** (≤100 testers, near-instant) → **Closed testing**
(email lists/Google Groups) → **Open testing** (public, listed) →
**Production**. Promotion reuses the reviewed artifact (Releases → Promote, or
API).

- **Staged rollout**: pick a percentage; bump manually (typical 1→5→10→20→50→100).
  Halt stops new deliveries (updated users keep it); resume at any percentage.
  Since 2025 you can halt even a fully-rolled-out release.
- **Managed publishing**: approved changes queue until you hit Publish —
  decouples review timing from launch timing.
- Review times (observed, no SLA): new apps 2–7 days; updates hours–2 days.

**New personal accounts** (created after Nov 2023): before production access,
a closed test with **≥12 opted-in testers continuously for 14 days** (still the
active rule mid-2026), then a production-access questionnaire. Organization
accounts are exempt.

## Automated uploads (Play Developer API / fastlane supply)

Setup: GCP project → enable **Google Play Android Developer API** → service
account (JSON key, or Workload Identity Federation for keyless CI) → Play
Console → Users and permissions → **invite the SA email like a normal user** —
grant release-to-testing but consider withholding "Release to production" as a
human gate. (The old "API access" linking page is retired.)

```bash
fastlane supply init                     # pull existing metadata
fastlane supply --aab app-release.aab --track internal \
  --json_key play-sa.json --package_name com.example.app

# Promote without re-upload, 10% staged:
fastlane supply --track internal --track_promote_to production \
  --rollout 0.1 --skip_upload_aab true --skip_upload_metadata true
```

Release notes: `fastlane/metadata/android/<locale>/changelogs/<versionCode>.txt`
(or `default.txt`). Raw API: Edits flow — insert edit → upload bundle →
`edits.tracks.update` (`releases[].releaseNotes`, `status:
completed|inProgress` + `userFraction`) → commit.

## Store listing requirements

- **Screenshots**: 2–8 per form factor, PNG/JPEG ≤8 MB, sides 320–3840 px,
  aspect ≤2:1; phones ideally ≥1080 px. Clean status bar via Demo Mode (see
  android-tools). Tablet/Chromebook/Wear/TV sets if targeted.
- **Icon**: 512×512 PNG ≤1 MB. **Feature graphic**: 1024×500 (required for
  promo placements/video).
- **Data safety form**: mandatory; must cover SDK collection (analytics/ads);
  Android ID counts as "Device or other IDs" (2025 update). Google
  cross-checks declarations against runtime behavior — mismatch = rejection or
  removal. Privacy policy URL must list the same categories.
- **Target API level**: currently **API 35** for new apps/updates; from
  **Aug 31, 2026**: API 36 for new apps/updates, ≥35 for existing apps to stay
  visible on new devices (extensions to Nov 1, 2026). Re-verify at release time.
- **Pre-launch report**: automatic on testing-track uploads — real-device
  crash/ANR/accessibility/security sweeps; add test credentials (App content →
  Pre-launch report settings) so crawlers get past login. Use it as a free
  device farm before promoting.

## Common policy failures

- **Data-safety mismatches** — top enforcement area (ML runtime cross-checks).
- **Sensitive permissions** (SMS, Call Log, MANAGE_EXTERNAL_STORAGE,
  QUERY_ALL_PACKAGES, background location, Accessibility misuse) each need a
  declaration form + prominent in-app disclosure + core-functionality
  justification.
- **Families policy**: under-13 in the target audience pulls in the whole
  policy set (self-certified ads SDKs only) — don't declare children
  unintentionally.
- **Account deletion**: apps with account creation must offer in-app deletion
  plus a web deletion URL in the data safety section.
- Crashes/ANRs flagged by the pre-launch report; metadata keyword stuffing.
