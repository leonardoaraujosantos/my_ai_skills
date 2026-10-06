---
name: ios-simulator
description: Drive the iOS Simulator from the CLI with xcrun simctl - boot/erase devices, install/launch apps with env vars, deep links, simulated push notifications, permission grants, screenshots/video with clean status bar, location/route simulation, log streaming, and stuck-simulator fixes. Use when the user says "run this on the simulator", "take a simulator screenshot", "test this deep link/push notification", "grant photo/location permission", "simulator won't boot", or "free up simulator disk space".
argument-hint: [device] [action]
---

# iOS Simulator Skill

CLI recipes for `xcrun simctl`. Verified against Xcode 26.0 (July 2026).

`<device>` = UDID, device name, or literal `booted` (if several are booted,
simctl picks one arbitrarily — prefer explicit UDIDs in scripts).

## Device management

| Task | Command |
|------|---------|
| List available devices | `xcrun simctl list devices available` |
| Booted device UDID | `xcrun simctl list devices --json \| jq -r '.devices[][] \| select(.state=="Booted") \| .udid'` |
| Create (prints UDID) | `UDID=$(xcrun simctl create "CI iPhone" "iPhone 17 Pro" iOS26.0)` |
| Boot **and wait until ready** | `xcrun simctl bootstatus "$UDID" -b` |
| Show the UI (boot doesn't) | `open -a Simulator` |
| Shutdown / erase / delete | `xcrun simctl shutdown all` · `erase <d>` (must be Shutdown) · `delete <d>` |
| Clone a pre-seeded device | `xcrun simctl clone <d> "Test copy"` (source shutdown first) |
| Rosetta boot (x86_64 app) | `xcrun simctl boot <d> --arch=x86_64` |

## App lifecycle

| Task | Command |
|------|---------|
| Install / uninstall | `xcrun simctl install booted path/to/MyApp.app` · `uninstall booted <bundle-id>` |
| Launch (prints PID) | `xcrun simctl launch booted <bundle-id>` |
| Relaunch cleanly | `xcrun simctl launch --terminate-running-process booted <bundle-id>` |
| Launch with console attached | `xcrun simctl launch --console-pty booted <bundle-id>` (blocks; app logs often go to stderr) |
| Launch args | append them: `... launch booted <bundle-id> -UITestMode YES` |
| Env vars | prefix host env with `SIMCTL_CHILD_`: `SIMCTL_CHILD_API_BASE_URL=http://localhost:8080 xcrun simctl launch booted <bundle-id>` |
| Terminate | `xcrun simctl terminate booted <bundle-id>` |
| App / data container path | `xcrun simctl get_app_container booted <bundle-id> app\|data\|groups` |
| Installed apps | `xcrun simctl listapps booted` |

## Deep links & universal links

```bash
xcrun simctl openurl booted "myapp://profile/42"
xcrun simctl openurl booted "https://example.com/item/42"   # universal link
```
If a universal link opens Safari instead of the app, the AASA association didn't
validate on the simulator — check the apple-app-site-association file first.

## Push notifications (local injection — no APNs)

```bash
xcrun simctl push booted com.example.MyApp payload.json
echo '{"aps":{"alert":"Hi"}}' | xcrun simctl push booted com.example.MyApp -
```

Payload rules: JSON object, must contain `aps`, ≤ 4096 bytes. With a top-level
`"Simulator Target Bundle": "com.example.MyApp"` key the bundle-id argument can
be omitted (and it's **required** for drag-and-drop `.apns` files onto the
Simulator window). Only plain remote notifications — no VoIP/complication/File
Provider pushes.

```json
{
  "Simulator Target Bundle": "com.example.MyApp",
  "aps": {
    "alert": { "title": "Order shipped", "body": "Order #42 is on its way" },
    "badge": 1, "sound": "default"
  }
}
```

## Permissions

```bash
xcrun simctl privacy booted grant photos com.example.MyApp
xcrun simctl privacy booted revoke location-always com.example.MyApp
xcrun simctl privacy booted reset all com.example.MyApp
```

Services (Xcode 26): `all`, `calendar`, `contacts`, `contacts-limited`,
`location`, `location-always`, `photos`, `photos-add`, `media-library`,
`microphone`, `motion`, `reminders`, `siri`.
**Not controllable here: `camera` and notifications permission** (many blog
posts claim `camera` works — it is not in the supported list). Grant/revoke may
terminate a running app; `pm clear`-style full reset is `erase`.

## Screenshots & video

```bash
# Screenshot (png default; --mask=alpha → transparent corners)
xcrun simctl io booted screenshot --type=png --mask=alpha shot.png

# Video: default codec is HEVC — use h264 for shareability.
xcrun simctl io booted recordVideo --codec=h264 --force demo.mp4 & REC=$!
# "Recording started" is printed to stderr when live. Drive the app, then:
kill -INT $REC; wait $REC        # SIGINT finalizes the file
```

### Clean status bar (App Store screenshot preset)

```bash
xcrun simctl status_bar booted override --time "9:41" \
  --dataNetwork wifi --wifiMode active --wifiBars 3 \
  --cellularMode active --cellularBars 4 \
  --batteryState charged --batteryLevel 100 --operatorName ''
xcrun simctl status_bar booted clear
```

Also: `--dataNetwork` accepts `5g`, `5g+`, `5g-uwb`, `5g-uc`, `lte+`, etc.
Dark mode for the shot: `xcrun simctl ui booted appearance dark`.

## Location

```bash
xcrun simctl location booted set 37.7749,-122.4194     # lat,lon ('.' decimal)
xcrun simctl location booted start --speed=15 --interval=1 \
  37.7749,-122.4194 37.7849,-122.4094                  # route between waypoints
xcrun simctl location booted clear
```

## Logs, defaults, media, misc

| Task | Command |
|------|---------|
| Stream app logs | `xcrun simctl spawn booted log stream --level=debug --predicate 'subsystem == "com.example.MyApp"'` (or `process == "MyApp"`) |
| Dump recent logs | `xcrun simctl spawn booted log show --last 5m --predicate '...'` |
| App defaults | `xcrun simctl spawn booted defaults write com.example.MyApp Key -bool YES` |
| Trust a proxy/mitm CA | `xcrun simctl keychain booted add-root-cert my-ca.pem` |
| Clipboard | `xcrun simctl pbcopy booted` (stdin→device) · `pbpaste booted` · `pbsync host booted` |
| Dark/light mode | `xcrun simctl ui booted appearance dark\|light` |
| Dynamic Type size | `xcrun simctl ui booted content_size accessibility-large` (or `increment`) |
| Seed photos/videos/contacts | `xcrun simctl addmedia booted photo.jpg video.mp4 contact.vcf` |
| Diagnostics bundle | `xcrun simctl diagnose -b --output=/tmp/simdiag` |
| Hardware keyboard off | `defaults write com.apple.iphonesimulator ConnectHardwareKeyboard -bool false` (restart Simulator.app) |

## Troubleshooting

**"Unable to boot device" / stuck simulator** — escalation ladder, stop when fixed:
1. `xcrun simctl shutdown all` and retry.
2. Kill CoreSimulator (relaunches on demand):
   `launchctl remove com.apple.CoreSimulator.CoreSimulatorService`
3. `xcrun simctl erase <device>` (must be shutdown first).
4. `xcrun simctl delete <device>` and recreate.
Also verify `xcode-select -p` points at the intended Xcode when several are installed.

**"Invalid device state"** — booting an already-booted device or erasing a booted
one; check `state` in `list devices --json`, `shutdown` before `erase`.

**Disk bloat** (runtimes live in a shared cryptex store, not per-Xcode):
```bash
xcrun simctl runtime list
xcrun simctl runtime delete --notUsedSinceDays 30 --dry-run   # then without --dry-run
xcrun simctl delete unavailable                               # stale device stubs
xcrun simctl runtime dyld_shared_cache remove --all           # dyld cache bloat
```

**Architecture errors** (`incompatible architecture`): x86_64-only .app on an
arm64 simulator — rebuild for arm64 sim, or boot the device under Rosetta
(`boot --arch=x86_64`).

**Simulator limitations** (don't debug these as app bugs): no real camera, no
real APNs delivery (only `simctl push` injection), no VoIP/complication pushes,
keychain/attestation and some Metal features differ from hardware.

Note: `simctl reboot` exists only in later Xcode 26.x — feature-detect and fall
back to `shutdown` + `bootstatus -b`.
