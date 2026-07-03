# Capturing mobile app screenshots

Three paths, in order of effort. Pick by what the product actually is.

## 1. Mobile web / PWA → Playwright device emulation (easiest)
If the product is a responsive web app or PWA, just emulate a phone in the storyboard — no simulator needed:
```json
{ "base": "https://app.example.com", "device": "iPhone 15", "state_file": "auth.json",
  "scenes": [ { "out": "shots/m-home.png", "steps": [ {"goto":"/app"}, {"wait":2500}, {"screenshot":null} ] } ] }
```
`capture.py` passes the Playwright device descriptor (correct viewport, DPR, touch, UA). Any name from Playwright's device registry works (`"Pixel 7"`, `"iPhone 13 Mini"`, …).

## 2. Native iOS — Simulator + `xcrun simctl`
For a real native/Flutter/React-Native iOS build:
```bash
xcrun simctl list devices                       # find/boot a device
xcrun simctl boot "iPhone 15"
open -a Simulator
xcrun simctl install booted /path/App.app       # or run from Xcode / flutter run
xcrun simctl launch booted <bundle.id>
# drive the UI (taps) — see below — then capture:
xcrun simctl io booted screenshot shots/ios-home.png
```
Driving the UI: use **Appium** (XCUITest driver) or the app's own **UI test target** (XCUITest / Flutter `integration_test`) to navigate to each screen, taking a `simctl io … screenshot` (or the framework's screenshot API) at each stop. For a quick pass you can also tap by coordinates via `xcrun simctl` is limited — Appium is the reliable driver.

## 3. Native Android — emulator + `adb`
```bash
emulator -list-avds && emulator -avd <avd> &     # or start from Android Studio
adb install app-debug.apk
adb shell am start -n <package>/<activity>
# drive via Appium (UiAutomator2) or espresso, then capture:
adb exec-out screencap -p > shots/android-home.png
```

## Flutter (either platform)
`flutter run` on a booted simulator/emulator, then either:
- drive with `flutter drive` / `integration_test` and call `binding.takeScreenshot(...)`, or
- capture with `xcrun simctl io booted screenshot` (iOS) / `adb exec-out screencap` (Android).

## Assembling
Mobile screenshots are portrait and small — in the PDF manual they look best 2-up or centered at reduced width (put two related shots side by side in one `<figure>`, or set a narrower image; edit `manual_pdf.py`'s `figure img` width for a mobile deck). For slides, place a phone-frame image on one side using the `section` slide type.

## Notes
- Boot the simulator/emulator once and reuse it across scenes (booting is slow).
- Log in through the app's real flow the first time; if the app persists a session, later runs skip login.
- Same hygiene as web: only apps you're authorized to test; scrub credentials afterward.
