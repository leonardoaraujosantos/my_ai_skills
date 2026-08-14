# Sentry — Android

Docs: https://docs.sentry.io/platforms/android/ (append `.md` for Markdown).

Captures crashes (JVM and NDK), ANRs, slow/frozen frames, network and DB spans,
profiling, logs, and session replay.

## Install — use the wizard

```bash
npx @sentry/wizard@latest -i android
```

It adds the Sentry Android Gradle plugin, writes the DSN into `AndroidManifest.xml`,
and wires ProGuard/R8 mapping upload — the last part is the reason to use it.

## Gradle plugin (manual)

```kotlin
// app/build.gradle.kts
plugins {
    id("io.sentry.android.gradle") version "<latest>"
}

sentry {
    org.set("<your-org-slug>")
    projectName.set("<your-project-slug>")
    // authToken comes from SENTRY_AUTH_TOKEN or sentry.properties — never commit it
    includeProguardMapping.set(true)
    autoUploadProguardMapping.set(true)
    tracingInstrumentation {
        enabled.set(true)     // auto DB/OkHttp spans via bytecode instrumentation
    }
    // uploads native (NDK) debug symbols too
    uploadNativeSymbols.set(true)
}
```

Check the current plugin version at
https://github.com/getsentry/sentry-android-gradle-plugin/releases — the plugin also
pulls in a matching `sentry-android` SDK version, so you usually don't declare the SDK
dependency separately.

## Configure via AndroidManifest.xml

The manifest is the default configuration surface (no code required):

```xml
<application>
    <meta-data android:name="io.sentry.dsn"
        android:value="https://<key>@o<orgId>.ingest.sentry.io/<projectId>" />
    <meta-data android:name="io.sentry.send-default-pii" android:value="true" />
    <meta-data android:name="io.sentry.traces.sample-rate" android:value="0.1" />
    <meta-data android:name="io.sentry.traces.profiling.session-sample-rate" android:value="0.1" />
    <meta-data android:name="io.sentry.traces.profiling.lifecycle" android:value="trace" />
    <meta-data android:name="io.sentry.logs.enabled" android:value="true" />
    <meta-data android:name="io.sentry.session-replay.on-error-sample-rate" android:value="1.0" />
    <meta-data android:name="io.sentry.session-replay.session-sample-rate" android:value="0.1" />
    <meta-data android:name="io.sentry.environment" android:value="production" />
</application>
```

Manifest values are baked into the APK, so per-environment values need build-variant
manifest placeholders (`manifestPlaceholders["sentryDsn"] = ...`) or the programmatic
init below.

## Programmatic init

Use this when the DSN or sample rates must vary at runtime. Init in `Application.onCreate`
before anything else, and disable the auto-init in the manifest:

```xml
<meta-data android:name="io.sentry.auto-init" android:value="false" />
```

```kotlin
import io.sentry.android.core.SentryAndroid
import io.sentry.SentryLevel

class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        SentryAndroid.init(this) { options ->
            options.dsn = BuildConfig.SENTRY_DSN
            options.environment = BuildConfig.BUILD_TYPE
            options.release = "${BuildConfig.APPLICATION_ID}@${BuildConfig.VERSION_NAME}+${BuildConfig.VERSION_CODE}"
            options.isDebug = BuildConfig.DEBUG
            options.isSendDefaultPii = true
            options.tracesSampleRate = 0.1
            options.isEnableLogs = true
            options.setDiagnosticLevel(SentryLevel.WARNING)
        }
    }
}
```

An empty/blank DSN disables the SDK — use that for debug builds instead of branching
around every Sentry call.

## Verify

```kotlin
try {
    throw Exception("Sentry test exception")
} catch (e: Exception) {
    Sentry.captureException(e)
}
```

For a real crash test, throw off a button tap and let it propagate. Crashes are cached
and sent on next launch.

## ProGuard / R8 mapping — required for readable traces

With `autoUploadProguardMapping.set(true)` the plugin uploads
`app/build/outputs/mapping/<variant>/mapping.txt` on every release build and injects a
UUID into the APK so Sentry matches events to the right mapping automatically.

If you build in CI, export `SENTRY_AUTH_TOKEN` there. If you disable auto-upload,
upload manually:

```bash
sentry-cli upload-proguard \
  --uuid <the-uuid-from-sentry-debug-meta.properties> \
  app/build/outputs/mapping/release/mapping.txt
```

Symptom of a missing mapping: stack frames full of `a.b.c.d(SourceFile:1)`.

## NDK / native crashes

`uploadNativeSymbols.set(true)` uploads `.so` debug symbols. Add
`uploadSourceContext.set(true)` for source snippets. Native crashes only symbolicate if
the build kept debug info — check that your CMake/NDK config isn't stripping before
the plugin runs.

## Common gotchas

- **Multi-process apps** re-run `Application.onCreate` per process; init is per-process
  and that's fine, but guard any one-time side effects.
- **Session replay masks all views by default.** Unmask deliberately
  (`options.sessionReplay.unmaskViewClasses`), never on a screen with customer data.
- **ANR detection** can be noisy on low-end devices; tune
  `options.anrTimeoutIntervalMillis` before disabling it.
- **Jetpack Compose**: add the `sentry-compose-android` artifact for composition spans
  and better replay masking.
- **OkHttp spans** require the `sentry-android-okhttp` integration or the Gradle
  tracing instrumentation — plain OkHttp calls otherwise show as one opaque span.
