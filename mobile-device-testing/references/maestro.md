# Maestro — Cross-Platform UI Flows (verified July 2026, CLI 2.6.x)

Black-box YAML UI testing over the accessibility tree. One syntax for Android +
iOS + Web; no test code compiled into the app.

**Platform support (the critical asymmetry):** Android = emulators AND real
devices over adb. iOS = **simulators only — physical iOS devices are not
supported** (verbatim in current docs; Maestro Cloud rejects device builds).
Real-iPhone coverage requires XCUITest (`references/ios-device.md`).

## Install

```bash
curl -fsSL "https://get.maestro.mobile.dev" | bash     # or:
brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro
```

Requires **Java 17+** (2.x; the 1.x line is obsolete). Pin:
`MAESTRO_VERSION=2.6.1 curl -Ls "https://get.maestro.mobile.dev" | bash`.
Note: `maestro studio` (browser) was removed in 2.6.0 — Studio is now a
desktop app from studio.maestro.dev; `maestro hierarchy` prints the live view
tree as JSON.

## Flow anatomy

```yaml
appId: com.example.app          # package / bundle id
tags: [smoke]
env: { DEFAULT_TIMEOUT: 5000 }
onFlowStart: [ runFlow: setup.yaml ]
---
- launchApp:
    clearState: true
    permissions: { all: deny, camera: allow, location: allow }
- tapOn: "Sign in"                       # string = regex text selector
- tapOn: { id: "email_field" }
- inputText: ${USERNAME}
- tapOn: { id: "submit", retryTapIfNoChange: true }
- assertVisible: { text: "Welcome.*" }   # auto-retries up to 7 s
- takeScreenshot: after-login
```

## Command cheat sheet

| Need | Command |
|------|---------|
| Deep link | `- openLink: myapp://settings` (`autoVerify:`/`browser:` Android-only; iOS first launch may show a confirm dialog — handle with conditional runFlow) |
| Scroll to element | `- scrollUntilVisible: { element: { text: "Terms" }, direction: DOWN, timeout: 20000 }` |
| Swipe | `- swipe: { direction: LEFT }` or `{ start: "90%,50%", end: "10%,50%" }` |
| Wait (fail on timeout) | `- extendedWaitUntil: { visible: { id: "list" }, timeout: 10000 }` |
| Wait for animation (never fails) | `- waitForAnimationToEnd: { timeout: 5000 }` |
| Conditional | `- runFlow: { when: { visible: "Accept cookies" }, commands: [ tapOn: "Accept" ] }` (also `platform: iOS`, `true: ${expr}`) |
| Loop / retry | `- repeat: { times: 3, commands: […] }` · `- retry: { maxRetries: 3, commands: […] }` (cap is 3) |
| Subflow with env | `- runFlow: { file: login.yaml, env: { USER: admin } }` |
| Tolerate failure | any command + `optional: true, label: "…"` |
| JS | `${expr}` inline · `- runScript: script.js` (GraalJS; shared `output` object; built-in `http.get/post`, `faker`) |
| Grab text | `- copyTextFrom: { id: "code" }` → `${maestro.copiedText}` |
| Location / route | `- setLocation: { latitude: 52.36, longitude: 4.88 }` (Android API 31+) · `- travel: { points: […], speed: 7900 }` |
| Seed media | `- addMedia: ["./assets/photo.png"]` |
| Video | `- startRecording: demo` … `- stopRecording` (MP4) |
| Kill / wipe | `- killApp` · `- clearState` (iOS: reinstalls) · `- clearKeychain` |
| System keys | `- pressKey: enter` · `- back` (**Android/Web only**) · `- hideKeyboard` (flaky — prefer tapping a dead area) |
| Random input | `- inputRandomEmail` · `- inputRandomPersonName` · `- inputRandomNumber: { length: 6 }` |

Selectors: `text` (regex), `id` (regex; Compose needs
`Modifier.semantics { testTagsAsResourceId = true }`), `index`, `point`,
relational (`below`, `above`, `childOf`, `containsDescendants`), state
(`enabled`, `checked`, `focused`, `selected`).

## Running & CI

```bash
maestro test flow.yaml
maestro test .maestro/ --include-tags=smoke --exclude-tags=wip
maestro test --format junit --output report.xml .maestro/
maestro --device emulator-5554 test flow.yaml
maestro test -e USERNAME=x -e PASSWORD=y flow.yaml     # env; MAESTRO_* shell vars auto-pass
maestro start-device --platform ios --device-model iPhone-11 --device-os iOS-18-2
```

Workspace `config.yaml`: `flows: ["auth/*", "tests/**"]`,
`includeTags/excludeTags`, `executionOrder: { continueOnFailure: false,
flowsOrder: […] }` (default order is non-deterministic — pin it).

**Sharding** (devices must already be booted, count must match):
`--shard-split 3` divides the suite across 3 devices; `--shard-all 3` runs the
whole suite on each (flake hunting). Use `${MAESTRO_SHARD_INDEX}` /
`${MAESTRO_DEVICE_UDID}` to disambiguate artifacts.

Flakiness levers: 7 s built-in assertion retry, `retry` (max 3),
`retryTapIfNoChange`, `extendedWaitUntil`, `optional: true`,
`MAESTRO_DRIVER_STARTUP_TIMEOUT` (default 15 s). CI env:
`MAESTRO_CLI_NO_ANALYTICS=1`, `MAESTRO_DISABLE_UPDATE_CHECK=1`.

**Maestro Cloud** (the product was briefly "Robin" in 2024–25, now Maestro
Cloud again): `maestro cloud --api-key K --project-id P --app-file app.apk
--flows ./maestro` — upload the folder so subflows/scripts come along; iOS =
simulator .app zip only. GitHub Action: `mobile-dev-inc/action-maestro-cloud`.
Self-hosted alternative: plain `maestro test` + sharding on your own
emulators — free and fully supported.

## Maestro vs XCUITest/Espresso

Maestro = black-box, cross-platform E2E journeys, smoke suites, agent-friendly
(there's a `maestro mcp` server), zero app changes; tolerant auto-waiting.
XCUITest/Espresso = white-box, in-process sync (idling resources), app
internals/mocks, performance metrics, and the only way to drive a **real
iPhone**. Rule of thumb: Maestro for cross-platform flows on
emulators/simulators + real Android hardware; XCUITest/Espresso for
component-level tests and physical-iOS coverage.
