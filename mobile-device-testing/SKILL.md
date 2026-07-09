---
name: mobile-device-testing
description: Run mobile tests on real connected devices and device farms - iOS physical-device prerequisites (Developer Mode, pairing, wireless), XCUITest on hardware with signing/error fixes, build-once .xctestrun distribution, Maestro cross-platform YAML UI flows, Firebase Test Lab (Android+iOS), Gradle-managed devices, and farm routing (AWS/BrowserStack/Sauce). Use when the user says "run tests on my iPhone/Android phone", "test on a real device", "device farm / Firebase Test Lab", "write a Maestro flow", "UI test this app end-to-end", or "the test runner won't install on device".
argument-hint: [ios|android|maestro|farm] [action]
---

# Mobile Device Testing Skill

Testing on real hardware and device clouds. Verified July 2026 (Xcode 26,
Maestro 2.6, current gcloud). Complements: **xcode-tools** (xcodebuild/xcresult
mechanics), **android-tools** (adb/emulator), **mobile-profiling** (perf on
device), **mobile-publish** (pre-launch report).

- `references/ios-device.md` — Developer Mode, pairing/trust, wireless,
  XCUITest signing on hardware, error→fix table, .xctestrun distribution
- `references/maestro.md` — cross-platform YAML UI flows, selectors, CI
  sharding, cloud
- `references/device-farms.md` — Firebase Test Lab (Android + iOS),
  Gradle-managed devices, AWS/BrowserStack/Sauce routing, Xcode Cloud limits

## Routing — what runs where (the constraints that decide everything)

| Target | XCUITest | Espresso/UIAutomator | Maestro |
|--------|----------|----------------------|---------|
| iOS simulator | ✅ | — | ✅ |
| **Real iPhone/iPad** | ✅ (only option) | — | ❌ **not supported** |
| Android emulator | — | ✅ | ✅ |
| **Real Android device** | — | ✅ | ✅ (plain adb) |
| Firebase Test Lab | ✅ (physical only) | ✅ | via BrowserStack instead |
| Xcode Cloud | simulators only | — | — |

Decision rules:
- **Real Android device**: cheapest path is Maestro over adb (no
  instrumentation, no build changes) for E2E flows; Espresso for white-box/
  component tests.
- **Real iOS device**: XCUITest is the only game in town — go straight to
  `references/ios-device.md` for the prerequisite checklist (Developer Mode,
  trust, runner signing) because that's where all the time goes.
- **No devices on hand**: Firebase Test Lab (free daily quota) or the Play
  pre-launch report; BrowserStack if you need Maestro-in-the-cloud or wide
  device coverage.
- **Cross-platform suite for one app**: Maestro flows for journeys (run on
  Android hardware + iOS simulators) + a thin XCUITest smoke suite for real-
  iPhone confidence.

## Fastest useful commands

```bash
# Real Android device, zero setup beyond adb:
maestro test .maestro/smoke.yaml

# Real iPhone (after prerequisites — see ios-device.md):
xcodebuild test -scheme App -destination 'platform=iOS,id=<UDID>' \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration

# No device? Free FTL robo crawl (no test code):
gcloud firebase test android run --type robo --app app-debug.apk \
  --device model=oriole,version=33

# List every attached device, both platforms:
xcrun devicectl list devices; adb devices -l
```

## Golden rules

1. **Check prerequisites before debugging tests.** 90% of "tests won't run on
   my iPhone" is Developer Mode off, an untrusted developer profile, a locked
   screen, or the runner app missing the device UDID in its profile — the
   error→fix table in `ios-device.md` covers each.
2. **Build once, run everywhere**: `build-for-testing` → `.xctestrun` →
   `test-without-building` per device (iOS); `assembleDebug` +
   `assembleDebugAndroidTest` APK pair (Android). This is also exactly what
   device farms consume.
3. **Keep device state test-owned**: Maestro `clearState`, `pm clear`,
   `resetAuthorizationStatus` — never depend on leftover state; it's the top
   flake source on shared hardware.
4. **Farms bill per device-minute** — shard deliberately, set explicit
   `--timeout`, and use the free tiers first (FTL daily quota, Play
   pre-launch report).
5. Real-device runs are slower and flakier than simulator/emulator runs by
   nature — reserve hardware for what hardware uniquely validates: camera,
   push, performance/thermals, Bluetooth, real networks, and release-candidate
   smoke tests.
