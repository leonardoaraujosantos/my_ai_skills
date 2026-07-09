---
name: android-tools
description: Native Android development CLI recipes - emulator/AVD management (headless boot, snapshots, network/battery/GPS via console), adb essentials (install flags, deep links, permission grants, screenshots/screenrecord with clean status bar, logcat filtering, run-as file access), crash/ANR/tombstone debugging, and Gradle build triage (dependency conflicts, manifest merger, R8, AGP 9). Use when the user says "run this on the Android emulator", "adb screenshot/logcat", "test this deep link", "parse this ANR/bugreport", "gradle build fails", "duplicate class", or "R8 crash in release".
argument-hint: [emulator|adb|debug|gradle] [action]
---

# Android Tools Skill

CLI recipes for native Android dev. Verified July 2026 (AGP 9.2, Gradle 9.4,
platform-tools current). Tools live under `$ANDROID_HOME` (macOS default
`~/Library/Android/sdk`): `cmdline-tools/latest/bin/{sdkmanager,avdmanager}`,
`platform-tools/adb`, `emulator/emulator`, `build-tools/<ver>/`.

Deeper references — read when the task goes past quick recipes:
- `references/debugging.md` — ANRs, tombstones/ndk-stack, StrictMode, dumpsys
- `references/gradle.md` — AGP 9 version matrix, dependency conflicts, manifest
  merger, R8/ProGuard, config cache, signing/keytool

## Emulator / AVD

```bash
# Install a system image + create an AVD (echo "no" skips the hw-profile prompt)
sdkmanager --install "system-images;android-36;google_apis;arm64-v8a"
echo "no" | avdmanager create avd -n ci_avd \
  -k "system-images;android-36;google_apis;arm64-v8a" -d pixel_7 --force
# image variants: google_apis (rootable) | google_apis_playstore (Play, no root) | default (smallest)

# Headless CI launch
emulator -avd ci_avd -no-window -no-audio -no-boot-anim \
  -gpu swiftshader_indirect -no-snapshot -wipe-data &

# Wait for full boot, then stabilize for tests
adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done'
adb shell input keyevent 82                                  # dismiss keyguard
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
```

Snapshot flags: `-no-snapshot-load` = cold boot; `-snapshot <name>` named;
`-read-only` lets multiple emulators share one AVD; `-port 5556` pins the serial
(`emulator-5556`). AVD tuning: edit `~/.android/avd/<name>.avd/config.ini`
(`hw.ramSize`, `disk.dataPartition.size=8G`, `hw.keyboard=yes`).

**Device-state simulation** — prefer `adb emu <cmd>` (auth handled) over telnet:

| Simulate | Command |
|----------|---------|
| Slow network | `adb emu network speed edge` · `network delay umts` |
| Battery level/state | `adb emu power capacity 15` · `power ac off` |
| GPS fix | `adb emu geo fix -122.084 37.422` (**longitude first**) |
| Incoming call / SMS | `adb emu gsm call +1555…` · `sms send +1555… "Hi"` |
| Rotate / fold | `adb emu rotate` · `fold` / `unfold` |
| Fingerprint touch | `adb emu finger touch 1` |
| Snapshot save/load | `adb emu avd snapshot save mysnap` / `load mysnap` |
| Clean shutdown | `adb emu kill` |

## adb essentials

```bash
adb devices -l                          # serials; target with -s <serial> (-e emulator, -d USB)
adb pair 192.168.1.50:37123             # wireless (Android 11+): pair-code port, then
adb connect 192.168.1.50:40567          # the separate connect port

adb install -r -g app-debug.apk         # -r reinstall keep data, -g grant all runtime perms,
                                        # -d allow downgrade, -t test-only APKs
adb uninstall com.example.app           # -k keeps data
# AABs need bundletool (not directly installable):
bundletool build-apks --bundle=app.aab --output=app.apks --ks=... --ks-key-alias=...
bundletool install-apks --apks=app.apks
```

| Task | Command |
|------|---------|
| Deep link | `adb shell am start -W -a android.intent.action.VIEW -d "myscheme://path?id=42" com.example.app` |
| Clean launch activity | `adb shell am start -S -n com.example.app/.MainActivity` (with extras: `--es key val --ei n 3 --ez flag true`) |
| Force-stop / wipe data | `adb shell am force-stop <pkg>` · `pm clear <pkg>` (**also revokes runtime perms**) |
| Grant/revoke permission | `adb shell pm grant <pkg> android.permission.ACCESS_FINE_LOCATION` / `pm revoke …` |
| Special app-ops perm | `adb shell appops set <pkg> SYSTEM_ALERT_WINDOW allow` |
| Push/pull files | `adb push f /sdcard/Download/` · `adb pull /sdcard/…` |
| App-private file (binary-safe) | `adb exec-out run-as <pkg> cat databases/app.db > app.db` (grab `-wal`/`-shm` too) |
| Doze test | `adb shell cmd deviceidle force-idle` |

## Screenshots & screen recording

```bash
adb exec-out screencap -p > screen.png          # exec-out avoids binary corruption
adb shell screenrecord --time-limit 30 /sdcard/demo.mp4   # max 3 min, no audio; Ctrl-C finalizes
adb pull /sdcard/demo.mp4 && adb shell rm /sdcard/demo.mp4
```

Clean status bar (Demo Mode) before store screenshots:

```bash
adb shell settings put global sysui_demo_allowed 1
adb shell am broadcast -a com.android.systemui.demo -e command enter
adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 1000
adb shell am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false
adb shell am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4
adb shell am broadcast -a com.android.systemui.demo -e command notifications -e visible false
adb shell am broadcast -a com.android.systemui.demo -e command exit
```

## logcat

```bash
adb logcat MyApp:D OkHttp:W *:S                        # only these tags, silence rest
adb logcat --pid=$(adb shell pidof -s com.example.app) # one process
adb logcat -e "Exception|ANR"                          # regex on message
adb logcat -b crash -d > crash.log                     # crash buffer, dump & exit
adb logcat -c                                          # clear before a repro run
adb logcat -v color -t 500                             # colorized, last 500 lines
adb logcat -T '07-09 12:00:00.000'                     # since timestamp
```

Buffers: `-b main|system|events|crash|radio|all`. Formats: `-v threadtime`
(default), `time`, `color`, `long`, `epoch` (combine: `-v time,color`).

## Crash / ANR quick path

```bash
adb bugreport bug.zip          # always works unrooted; ANR traces at FS/data/anr/,
                               # tombstones at FS/data/tombstones/
adb logcat -b crash -d         # fatal exceptions + native abort messages
ndk-stack -sym app/build/intermediates/merged_native_libs/debug/out/lib/arm64-v8a -dump tombstone_00
```

In an ANR trace: find the `"main"` thread block; `held by thread N` lines expose
lock contention; `am_anr` in `-b events` gives the reason. Full playbook (incl.
dumpsys meminfo/gfxinfo/batterystats): `references/debugging.md`.

## Gradle quick path

```bash
./gradlew :app:dependencyInsight --dependency okhttp --configuration releaseRuntimeClasspath
./gradlew :app:dependencies --configuration releaseRuntimeClasspath   # full tree
./gradlew assembleDebug --scan                                        # deep build timeline
./gradlew --stop                                                      # kill stale daemons
```

Fast facts (July 2026): AGP 9.2 needs Gradle ≥ 9.4.1 and JDK 17+; AGP 9 has
**built-in Kotlin** — don't apply `org.jetbrains.kotlin.android` with the new
DSL. R8 missing rules land in `app/build/outputs/mapping/release/missing_rules.txt`;
retrace with `retrace mapping.txt stacktrace.txt`. Manifest merger blame:
`app/build/outputs/logs/manifest-merger-debug-report.txt`. Full triage playbook:
`references/gradle.md`.
