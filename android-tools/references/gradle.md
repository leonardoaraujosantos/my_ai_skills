# Gradle / AGP Build Triage

## Version matrix (July 2026 — re-verify before pinning versions)

| Component | Current | Constraint |
|-----------|---------|-----------|
| AGP | 9.2.0 (9.0/9.1 in wide use) | AGP 9.2 needs Gradle ≥ 9.4.1; AGP 9.0 needs ≥ 9.1.0 |
| Gradle | 9.4.x | JDK 17 minimum to run builds |
| Kotlin | 2.3.x | AGP 9 bundles KGP (**built-in Kotlin**) |
| Build Tools | 36.0.0 (AGP 9.2 default) | max compileSdk: API 37 (AGP 9.2) |

AGP 9 migration gotchas: built-in Kotlin is on by default — **do not apply
`org.jetbrains.kotlin.android`** with the new DSL; `android.kotlinOptions` →
`kotlin {}` block; legacy Variant API removed. Temporary escape hatches:
`android.builtInKotlin=false`, `android.newDsl=false`.

```bash
./gradlew --version                              # Gradle + JVM in use
./gradlew wrapper --gradle-version 9.4.1         # upgrade wrapper
```

## Dependency conflicts

```bash
./gradlew :app:dependencies --configuration releaseRuntimeClasspath   # full tree
./gradlew :app:dependencyInsight --dependency okhttp \
  --configuration releaseRuntimeClasspath        # WHY a version won
./gradlew buildEnvironment                       # buildscript classpath tree
```

```kotlin
configurations.all {
    resolutionStrategy {
        force("com.squareup.okhttp3:okhttp:4.12.0")
        failOnVersionConflict()          // surface instead of silent newest-wins
    }
}
dependencies {
    implementation("com.squareup.okhttp3:okhttp") { version { strictly("4.12.0") } }
    implementation(platform("androidx.compose:compose-bom:2026.05.00"))  // BOM aligns families
    implementation("androidx.compose.material3:material3")               // version from BOM
}
```

## Failure playbook

**Duplicate class** (`Duplicate class com.x.Y found in modules …`)
Find the two providers with the dependency tree, then exclude the loser:
`implementation("…") { exclude(group = "com.google.guava", module = "listenablefuture") }`.
Classic case: guava `listenablefuture:1.0` vs the `9999.0-empty` stub.

**Manifest merger failed** (`:app:processDebugMainManifest`)
- Merged result: `app/build/intermediates/merged_manifests/debug/AndroidManifest.xml`
- Blame report: `app/build/outputs/logs/manifest-merger-debug-report.txt`
- Fixes (need `xmlns:tools`): `tools:replace="android:label"` on `<application>`,
  `tools:node="remove|merge"` on the offending element; library minSdk conflicts
  → `<uses-sdk tools:overrideLibrary="com.lib.pkg"/>` (last resort).

**R8/ProGuard — release-only crashes, missing classes**
- R8 writes suggested rules to `app/build/outputs/mapping/release/missing_rules.txt`
  → paste into `proguard-rules.pro`.
- Retrace an obfuscated stack:
  `$ANDROID_HOME/cmdline-tools/latest/bin/retrace app/build/outputs/mapping/release/mapping.txt stacktrace.txt`
- Why was a class kept/removed: `-whyareyoukeeping class com.example.Foo`;
  shrinker also emits `usage.txt` (removed), `seeds.txt` (kept), and
  `configuration.txt` (final merged rules) next to `mapping.txt`.
- Typical rules: `-keep class com.example.model.** { *; }` (reflection/Gson),
  `-keepattributes Signature,*Annotation*`; prefer `@Keep` in code.
- Test shrinking early: set `isMinifyEnabled = true` on a debug-variant copy.

**Daemon OOM** (`Expiring Daemon because JVM heap space is exhausted`)
```properties
# gradle.properties
org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError
kotlin.daemon.jvmargs=-Xmx4g
```
Then `./gradlew --stop` to kill stale daemons.

**Configuration cache problems** (default-on in recent Gradle)
```bash
./gradlew build --configuration-cache-problems=warn   # triage without failing
./gradlew build --no-configuration-cache              # bisect: is CC the cause?
# report: build/reports/configuration-cache/<hash>/…-report.html
```
Common offenders: env/system props read at configuration time (use
`providers.environmentVariable("X")`), `project` captured in `doLast`, old
plugins — check plugin updates first.

## Build performance

```bash
./gradlew assembleDebug --scan       # Develocity scan (deep timeline, cache misses)
./gradlew assembleDebug --profile    # local HTML report: build/reports/profile/
./gradlew :app:assembleDebug -x lint -x test
```

```properties
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.configuration-cache=true
```

## Signing & keytool

Debug keystore: `~/.android/debug.keystore` (storepass `android`, alias
`androiddebugkey`).

```bash
keytool -genkeypair -v -keystore release.keystore -alias release \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$STORE_PASS" -keypass "$KEY_PASS" -dname "CN=Example, O=Co, C=US"

# SHA-1/SHA-256 fingerprints (Firebase / Maps / App Links)
keytool -list -v -keystore release.keystore -alias release -storepass "$STORE_PASS" | grep -E "SHA1|SHA256"
$ANDROID_HOME/build-tools/36.0.0/apksigner verify --print-certs app-release.apk

# Manual sign (CI without Gradle)
zipalign -v -p 4 app-unsigned.apk app-aligned.apk
apksigner sign --ks release.keystore --ks-key-alias release --out app-release.apk app-aligned.apk
```

```kotlin
android {
    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("KEYSTORE_PATH") ?: "release.keystore")
            storePassword = System.getenv("STORE_PASS")
            keyAlias = "release"; keyPassword = System.getenv("KEY_PASS")
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
```

For Play App Signing / upload-key concepts see the mobile-publish skill.
