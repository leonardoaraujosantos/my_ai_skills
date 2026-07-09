---
name: xcode-tools
description: Xcode build-system CLI recipes - xcodebuild build/test/archive with destinations and test plans, parsing .xcresult bundles (failures, attachments, coverage), code-signing triage (certificates, provisioning profiles, CI keychains), crash symbolication (dSYM/atos/CrashSymbolicator), physical-device control with devicectl, and DerivedData/SPM cache hygiene. Use when the user says "build/test this iOS app from the CLI", "parse the xcresult", "code signing error/no signing certificate", "symbolicate this crash", "run on my iPhone", or "clean DerivedData/SPM cache".
argument-hint: [build|test|xcresult|signing|crash|device] [action]
---

# Xcode Tools Skill

CLI recipes for `xcodebuild` and friends. Verified against Xcode 26.0 (July 2026).
For simulator device control see the **ios-simulator** skill; for store
uploads see **mobile-publish**; for Instruments see **mobile-profiling**.

Deeper reference: `references/signing.md` — certificates, provisioning
profiles, error→fix table, CI temp-keychain recipe.

## Discovery

```bash
xcodebuild -list -json                             # schemes/targets/configs
xcodebuild -showdestinations -scheme MyApp -json   # -json works in Xcode 26
xcodebuild -showTestPlans -scheme MyApp
xcodebuild -showBuildSettings -scheme MyApp -json
```

## Build & test

```bash
xcodebuild build -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  -derivedDataPath ./DerivedData -quiet

rm -rf tests.xcresult   # -resultBundlePath fails if the path exists
xcodebuild test -scheme MyApp -testPlan CI \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  -resultBundlePath ./tests.xcresult \
  -only-testing:MyAppTests/LoginSuite -skip-testing:MyAppUITests
```

Destinations: `platform=iOS Simulator,name=…[,OS=26.0]` · `id=<simctl-UDID>` ·
`generic/platform=iOS` (archives) · `platform=iOS,name=<device>` · `platform=macOS`.
Multiple `-destination` flags test on several at once.

| Need | Flags |
|------|-------|
| Build once, test many | `build-for-testing` → `.xctestrun` in DerivedData → `test-without-building -xctestrun <file>` (no `-scheme` needed) |
| Readable output | `set -o pipefail && xcodebuild … 2>&1 \| xcbeautify` (xcpretty is unmaintained) or `-quiet` |
| Parallel tests | `-parallel-testing-enabled YES -maximum-parallel-testing-workers 4` |
| Flake hunting | `-retry-tests-on-failure` · `-test-iterations N` · `-run-tests-until-failure` |
| List tests without running | `-enumerate-tests -test-enumeration-format json` |
| Swift macros/plugins in CI | `-skipMacroValidation -skipPackagePluginValidation` (else the build blocks on interactive trust) |
| Portal access headless | `-allowProvisioningUpdates -authenticationKeyPath key.p8 -authenticationKeyID <ID> -authenticationKeyIssuerID <uuid>` |
| Coverage | `-enableCodeCoverage YES` (or enable in test plan) |

Swift Testing + XCTest both run under plain `xcodebuild test` (Xcode 16+) and
land in the same `.xcresult`. `-only-testing` quirk for functions inside a
`@Suite`: use doubled parens — `-only-testing:'MyTests/MySuite/myTest()()'` —
the safe automation form across Xcode versions.

Xcode 26 note: Swift explicitly-built modules are on by default; stale module
caches produce new failure signatures — clear `DerivedData/ModuleCache.noindex`
before suspecting compiler bugs.

## Parsing .xcresult (post-Xcode-16 shape)

Legacy `xcresulttool get object --format json` is deprecated. Current:

```bash
xcrun xcresulttool get test-results summary --path tests.xcresult   # counts + testFailures[] — usually all CI needs
xcrun xcresulttool get test-results tests --path tests.xcresult     # full test tree (IDs for below)
xcrun xcresulttool get test-results test-details --test-id 'MyAppTests/LoginSuite/testFoo()' --path tests.xcresult
xcrun xcresulttool get build-results --path build.xcresult          # warnings + errors as JSON
xcrun xcresulttool get log --path build.xcresult

# Screenshots & attachments (writes files + manifest.json)
xcrun xcresulttool export attachments --path tests.xcresult --output-path ./attachments --only-failures

# Coverage
xcrun xccov view --report --json tests.xcresult
xcrun xccov diff --json before.xcresult after.xcresult
```

JSON is the only output format (no `--format` flag); `--schema` prints the schema.

## Code signing (quick triage)

```bash
security find-identity -v -p codesigning        # "0 valid identities" = cert or private key missing
security cms -D -i profile.mobileprovision      # decode profile (pipe to plutil -p -)
codesign -dv --entitlements - MyApp.app         # what a binary is actually signed with
```

Profiles live at `~/Library/Developer/Xcode/UserData/Provisioning Profiles/`
(moved in Xcode 16; pre-16 tools still use `~/Library/MobileDevice/Provisioning
Profiles/` — check both). Full error→fix table and the CI temp-keychain recipe:
`references/signing.md`.

## Crash symbolication

```bash
# Match dSYM ↔ binary by UUID (must equal the crash's Binary Images UUID)
xcrun dwarfdump --uuid MyApp.app.dSYM
mdfind "com_apple_xcode_dsym_uuids == <UUID>"          # find a dSYM on disk

# Single address (load address -l from the crash's Binary Images section)
xcrun atos -o MyApp.app.dSYM/Contents/Resources/DWARF/MyApp -arch arm64 -l 0x100e00000 0x100e4a5d8

# Full .ips/.crash file (current tool, ships in Xcode 26)
python3 "/Applications/Xcode.app/Contents/SharedFrameworks/CoreSymbolicationDT.framework/Versions/A/Resources/CrashSymbolicator.py" \
  -d MyApp.app.dSYM -o symbolicated.crash -p crash.ips
```

dSYMs live in `MyApp.xcarchive/dSYMs/`. Legacy `symbolicatecrash` chokes on
modern JSON `.ips` files — use CrashSymbolicator.py. Field crash/hang data:
MetricKit delivers `MXDiagnosticPayload` on-device (not on simulator) — see
mobile-profiling.

## Physical devices — devicectl (replaced ios-deploy)

```bash
xcrun devicectl list devices --json-output devices.json   # JSON-to-FILE is the only stable machine interface
xcrun devicectl device install app --device <udid> MyApp.app
xcrun devicectl device process launch --device <udid> com.example.app \
  --console --terminate-existing        # --start-stopped waits for debugger; env via -e '{"K":"v"}'
xcrun devicectl device uninstall app --device <udid> com.example.app
```

No syslog subcommand — use `--console` on launch, or `log collect
--device-name "<name>"` then `log show` the .logarchive. Simulator logs:
`xcrun simctl spawn booted log stream --predicate 'subsystem == "com.foo"'`.

## Cache & dependency hygiene

| Problem | Fix |
|---------|-----|
| Weird incremental-build failures | `xcodebuild clean -scheme MyApp`; nuclear: `rm -rf ~/Library/Developer/Xcode/DerivedData` |
| SPM won't resolve / Package.resolved corrupt | delete `*.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved` + `rm -rf ~/Library/Caches/org.swift.swiftpm`, then `xcodebuild -resolvePackageDependencies` |
| CI SPM caching / drift | `-clonedSourcePackagesDirPath ./SourcePackages` + `-disableAutomaticPackageResolution` (fail rather than drift from Package.resolved) |
| Stale Swift modules (Xcode 26) | clear `DerivedData/ModuleCache.noindex` |
| Simulator runtime disk bloat | `xcrun simctl runtime delete --notUsedSinceDays 30` (see ios-simulator) |
| Fetch a runtime headlessly | `xcodebuild -downloadPlatform iOS` |

## Archive & export (hand-off to mobile-publish for upload)

```bash
xcodebuild archive -scheme MyApp -destination 'generic/platform=iOS' \
  -archivePath build/MyApp.xcarchive -allowProvisioningUpdates
xcodebuild -exportArchive -archivePath build/MyApp.xcarchive \
  -exportPath build/export -exportOptionsPlist ExportOptions.plist -allowProvisioningUpdates
```

Export `method` names (renamed Xcode 15.4; old names still accepted):
`app-store-connect` (was app-store), `release-testing` (was ad-hoc),
`debugging` (was development — **the default**), plus `enterprise`,
`developer-id`. Minimal TestFlight plist — `destination: upload` sends straight
to App Store Connect, skipping the .ipa step:

```xml
<dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>TEAMID</string>
</dict>
```
