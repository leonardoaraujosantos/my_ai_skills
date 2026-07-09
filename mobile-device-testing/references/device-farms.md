# Cloud Device Farms & Gradle-Managed Devices (verified July 2026)

## Firebase Test Lab — Android

```bash
# Instrumentation (Espresso/UIAutomator)
./gradlew assembleDebug assembleDebugAndroidTest
gcloud firebase test android run \
  --type instrumentation \
  --app app/build/outputs/apk/debug/app-debug.apk \
  --test app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk \
  --device model=oriole,version=33,locale=en,orientation=portrait \
  --timeout 15m

# Robo crawler — zero test code
gcloud firebase test android run --type robo --app app-debug.apk \
  --device model=oriole,version=33     # guided crawl: --robo-script robo_script.json
```

- Device catalog: `gcloud firebase test android models list` /
  `models describe <id>` / `versions list`. `--device` repeats for a matrix.
- `--app` accepts **.aab directly** (FTL builds a universal APK internally).
- Isolation: `--use-orchestrator` (NOT default) + `--environment-variables clearPackageData=1`.
- Sharding: `--num-uniform-shards=N` (each shard bills as a separate execution).
- Results land in GCS + Firebase console (URL printed); non-zero exit on failure = CI-friendly.
- **Quotas**: free (Spark) ≈ 60 min/day virtual + 30 min/day physical; Blaze
  overage $1/hr virtual, $5/hr physical, per-minute. Timeout max 45 m physical
  / 60 m virtual.

## Firebase Test Lab — iOS (physical devices only, no simulators)

```bash
xcodebuild -workspace MyApp.xcworkspace -scheme MyScheme \
  -derivedDataPath ./dd -sdk iphoneos build-for-testing     # MUST be -sdk iphoneos

cd dd/Build/Products
zip -r MyTests.zip Debug-iphoneos MyScheme_iphoneos*.xctestrun

gcloud firebase test ios run --test MyTests.zip \
  --device model=iphone14pro,version=16.6 --timeout 15m
```

- The zip = `.xctestrun` file + the `Debug-iphoneos` products dir (app + *-Runner.app).
- Small catalog (~20 models, `gcloud firebase test ios models list`); iOS 18+
  devices don't record result videos.
- No `--num-uniform-shards` on iOS — shard manually with edited
  `--xctestrun-file`s (`OnlyTestIdentifiers`). Flake retries:
  `--num-flaky-test-attempts 0–10`.
- iOS minutes always count against the *physical* quota.

## Gradle-Managed Devices (deterministic local emulators from Gradle)

```kotlin
android {
  testOptions {
    managedDevices {
      localDevices {
        create("pixel6api34") {
          device = "Pixel 6"; apiLevel = 34
          systemImageSource = "aosp-atd"   // atd images = stripped, faster, less flaky
        }
      }
      groups { create("phones") { targetDevices.add(devices["pixel6api34"]) } }
    }
  }
}
```

```bash
./gradlew pixel6api34DebugAndroidTest
./gradlew phonesGroupDebugAndroidTest      # group, parallel
# headless CI: -Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect
```

ATD caveat: docs say API 30 but images exist for 30–33+ — test your level.
Screenshot tests needing hardware rendering don't work on ATDs. Local sharding:
`android.experimental.androidTest.numManagedDeviceShards=2` in gradle.properties.

**FTL from Gradle** (`com.google.firebase.testlab` plugin, still 0.0.x alpha):
define `firebaseTestLab { managedDevices { create("ftlPixel3") { device = "Pixel3"; apiLevel = 30 } } }`
with `serviceAccountCredentials`, enable
`android.experimental.testOptions.managedDevices.customDevice=true`, run
`./gradlew ftlPixel3DebugAndroidTest`. Supports `numUniformShards` or
smart sharding via `targetedShardDurationMinutes`.

## Other farms — one-line routing

| Farm | Pick when |
|------|-----------|
| AWS Device Farm | Already on AWS (IAM/private devices/VPC); Appium/Espresso/XCUITest via `aws devicefarm schedule-run`; unmetered slots $250/device/mo |
| BrowserStack App Automate | Widest device coverage; **first-class Maestro cloud runner** (REST: upload app + flows zip); local tunneling |
| Sauce Labs | Mixed web+mobile on one vendor; uniquely offers cloud iOS **simulators**; `saucectl run` CLI |

## Xcode Cloud

Runs tests on **simulators only — it is CI, not a device farm**. Pair with FTL
iOS or BrowserStack for real-device coverage. Free tier ~25 compute h/month
(verify current tiers).

## Play pre-launch report (free implicit farm)

Every AAB uploaded to an internal/closed/open track gets an automatic FTL Robo
crawl on physical devices — crashes, ANRs, accessibility, security,
screenshots. Configure login credentials/deep links under Play Console → Test
and release → Pre-launch report settings. Details in mobile-publish.
