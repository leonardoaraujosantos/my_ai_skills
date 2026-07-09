# Testing on Real iOS Devices (verified July 2026, Xcode 26 / devicectl 477)

## Prerequisites checklist (each one blocks everything downstream)

1. **Developer Mode** (iOS 16+): Settings → Privacy & Security → Developer Mode
   → toggle → restart → confirm. The toggle only appears after the device has
   seen a dev signal (plug into a Mac with Xcode, or install a dev-signed
   build); missing after an OS update → reboot the device. Check from CLI:
   ```bash
   xcrun devicectl device info details --device <name|udid>
   # deviceProperties → developerModeStatus: enabled | disabled
   ```
   Off = device shows as "Unavailable Device" in destination lists.
2. **Pairing/trust**: first USB connect → "Trust This Computer?" → passcode.
   CLI: `xcrun devicectl manage pair --device <name>` (and `manage unpair`).
   Broken trust: device Settings → General → Transfer or Reset → Reset →
   Reset Location & Privacy, reconnect, re-trust.
3. **Wireless**: Xcode → Window → Devices and Simulators → "Connect via
   network" (after one wired connect). devicectl fully supports network
   devices (`transportType: localNetwork`, `.coredevice.local` hostnames);
   add `-destination-timeout 60` to xcodebuild for sleepy wireless devices.
4. **"Preparing device for development"**: Xcode enabling DDI services. If it
   fails: iOS newer than Xcode's DDI → **update Xcode** (no separate device
   support files in the CoreDevice era); locked device → unlock; stale
   connection → `xcrun devicectl device reboot --device <name>`.
5. **Unlocked screen for the whole run**: set Auto-Lock → Never on test
   devices (locked = "device is passcode protected" failures). Verify:
   `xcrun devicectl device info lockState --device <d>`.

## Running tests on a device

```bash
# Find the device (JSON-to-file is the only stable machine interface)
xcrun devicectl list devices --json-output d.json   # hardwareProperties.udid
xcrun xctrace list devices                          # one-liners incl. offline paired

xcodebuild test -scheme App -destination 'platform=iOS,id=<UDID>' \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
  -resultBundlePath out.xcresult
```

Note `platform=iOS` (not `iOS Simulator`), `id:` = hardware UDID.
`-allowProvisioningDeviceRegistration` auto-registers the UDID on the portal —
only works together with `-allowProvisioningUpdates` (headless: add the ASC
API key flags, see xcode-tools).

**Signing is the big difference vs simulator**: the app under test AND the
generated `<UITestTarget>-Runner.app` must both be signed with a development
profile covering this device's UDID. Set `DEVELOPMENT_TEAM` on the UI-test
target; wildcard `TEAM.*` profiles cover the runner (free accounts can't make
wildcards — give the runner an explicit bundle id).

### Build once, run on many devices (.xctestrun — how device farms work)

```bash
xcodebuild build-for-testing -scheme App -destination 'generic/platform=iOS' \
  -derivedDataPath ./dd -allowProvisioningUpdates
xcodebuild test-without-building \
  -xctestrun ./dd/Build/Products/App_iphoneos26.0-arm64.xctestrun \
  -destination 'platform=iOS,id=<UDID>'
```

The `.xctestrun` plist is editable between build and run (env vars,
`OnlyTestIdentifiers`). Fan out: multiple `-destination` flags +
`-maximum-concurrent-test-device-destinations N`.

## Error → fix table

| Error | Fix |
|-------|-----|
| "Unable to find a device matching the provided destination specifier" | Wrong name/UDID, disconnected, Developer Mode off, or unpaired — check `devicectl list devices`; bump `-destination-timeout` for wireless |
| "Failed to install or launch the test runner" (exit 65) | Runner signing: `DEVELOPMENT_TEAM` on the UI-test target, UDID in profile (`-allowProvisioningDeviceRegistration`), and trust the developer on-device: Settings → General → VPN & Device Management → Trust; delete stale `*-Runner.app` |
| "…inadequate entitlements or its profile has not been explicitly trusted by the user" | Trust the developer profile on the device (path above) |
| `ApplicationVerificationFailed` / "valid provisioning profile … not found" | Profile lacks this UDID or bundle id — regenerate/re-sign |
| "The device is passcode protected" | Unlock; Auto-Lock → Never for the run |
| Device listed as "Unavailable Device" | Developer Mode off → enable + reboot |

## devicectl scope (know its limits)

`devicectl` installs/launches apps (`device install app`, `device process
launch --console/--start-stopped/--terminate-existing`), copies files, lists
processes, reboots — but **has no test-run subcommand and no screenshot command
for hardware**. XCTest orchestration always goes through `xcodebuild
test`/`test-without-building`. Screenshots from device tests come from
XCTAttachment (below).

## XCUITest essentials for automation

- **Stable queries**: set `.accessibilityIdentifier("loginButton")` (SwiftUI)
  / `view.accessibilityIdentifier = "loginButton"`; query
  `app.buttons["loginButton"]`. Identifiers aren't localized — the core of
  reliable automation.
- **Single test on device**: `-only-testing:AppUITests/LoginTests/testValidLogin`.
- **Screenshots**:
  ```swift
  let att = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
  att.name = "after-login"; att.lifetime = .keepAlways   // default deletes on success
  add(att)
  ```
  Extract: `xcrun xcresulttool export attachments --path out.xcresult
  --output-path ./shots --only-failures`.
- **Permissions on hardware** (no `simctl privacy` equivalent):
  `app.resetAuthorizationStatus(for: .camera)` **before** `app.launch()`
  (it may terminate a running app), then handle the dialog with
  `addUIInterruptionMonitor` or springboard queries.
- **Device logs during runs**: `sudo log collect --device-name "<name>"` →
  `.logarchive`; live via Console.app or `pymobiledevice3 syslog live`.
- **Thermal/battery**: throttling skews XCTMetric perf tests — keep devices
  charged and check `ProcessInfo.processInfo.thermalState` in-test; skip perf
  assertions at `.serious`/`.critical`.

## Xcode Cloud

Simulators only — no physical devices. Real hardware in CI = your own Mac
runner with attached devices, or a device farm (`references/device-farms.md`).
