# Android Profiling — Perfetto, Macrobenchmark, simpleperf

## Perfetto system traces

Quickest path — the official helper (handles paths, pulls, opens the UI):

```bash
curl -O https://raw.githubusercontent.com/google/perfetto/main/tools/record_android_trace
chmod +x record_android_trace
./record_android_trace -o trace.perfetto-trace -t 30s -b 64mb \
  sched freq idle am wm gfx view binder_driver hal dalvik input res memory
```

Raw form (config from stdin — the universal invocation):

```bash
cat config.txtpb | adb shell perfetto -c - --txt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
adb pull /data/misc/perfetto-traces/trace.perfetto-trace
```

Minimal config skeleton:

```
buffers: { size_kb: 63488 fill_policy: RING_BUFFER }
duration_ms: 20000
data_sources: { config { name: "linux.ftrace"
  ftrace_config { ftrace_events: "sched/sched_switch" ftrace_events: "sched/sched_wakeup"
                  atrace_categories: "gfx" atrace_categories: "view" atrace_categories: "am"
                  atrace_apps: "com.example.myapp" } } }
data_sources: { config { name: "linux.process_stats" process_stats_config { scan_all_processes_on_start: true } } }
data_sources: { config { name: "android.surfaceflinger.frametimeline" } }
```

Key data sources: `linux.ftrace` (+`atrace_apps` captures the app's
`Trace.beginSection` slices), `android.surfaceflinger.frametimeline` (jank
classification), `android.heapprofd` (native heap sampling),
`android.java_hprof` (managed heap), `linux.sys_stats`.

Analysis: drag into https://ui.perfetto.dev, or headless SQL (the CI hook):

```bash
curl -LO https://get.perfetto.dev/trace_processor && chmod +x trace_processor
./trace_processor trace.perfetto-trace -q query.sql   # tables: slice, sched_slice, android_frame_timeline
```

## Macrobenchmark (androidx.benchmark:benchmark-macro-junit4, 1.3.x stable)

Separate `com.android.test` module; the target app needs
`<profileable android:shell="true"/>` and a release-like (minified) build.
**Real device, unlocked screen** — debuggable builds/emulators self-report
invalid.

```kotlin
@get:Rule val rule = MacrobenchmarkRule()

@Test fun startupCold() = rule.measureRepeated(
    packageName = "com.example.myapp",
    metrics = listOf(StartupTimingMetric()),        // timeToInitialDisplayMs (+ timeToFullDisplayMs with reportFullyDrawn())
    iterations = 10,
    startupMode = StartupMode.COLD,                 // COLD | WARM | HOT
) { pressHome(); startActivityAndWait() }

@Test fun scrollJank() = rule.measureRepeated(
    packageName = "com.example.myapp",
    metrics = listOf(FrameTimingMetric()),          // frameDurationCpuMs/frameOverrunMs P50–P99
    iterations = 5, startupMode = StartupMode.COLD,
) {
    startActivityAndWait()
    device.findObject(By.res(packageName, "recycler")).fling(Direction.DOWN)
    device.waitForIdle()
}
```

Run: `./gradlew :macrobenchmark:connectedBenchmarkReleaseAndroidTest`. Outputs
JSON + a Perfetto trace per iteration under
`outputs/connected_android_test_additional_output/`. Other metrics:
`TraceSectionMetric` (assert on your own trace sections), `PowerMetric`,
`MemoryUsageMetric` (experimental).

## Baseline Profiles

AOT-compile hot paths at install time (API 24+; `androidx.baselineprofile`
Gradle plugin + `BaselineProfileRule`):

```kotlin
@get:Rule val rule = BaselineProfileRule()
@Test fun generate() = rule.collect(
    packageName = "com.example.myapp", includeInStartupProfile = true,
) { pressHome(); startActivityAndWait() /* + critical journeys */ }
```

`./gradlew :app:generateBaselineProfile` (uses `aosp` Gradle-managed-device
images for the root requirement) → `baseline-prof.txt` under
`app/src/<variant>/generated/baselineProfiles/`. Verify impact by benchmarking
`CompilationMode.None()` vs `CompilationMode.Partial(BaselineProfileMode.Require)`
— typical cold-startup gain 15–30%.

## CPU — simpleperf (ships in the NDK)

```bash
# One-shot app profile (handles push/pull + binary_cache)
python3 $NDK/simpleperf/app_profiler.py -p com.example.myapp \
  -r "-e task-clock:u -f 1000 -g --duration 10"
python3 $NDK/simpleperf/report_html.py --add_source_code --source_dirs src/  # flamegraph tab
python3 $NDK/simpleperf/report.py -g                                          # text
```

Profiles Java + native together (full managed support Android 9+). App must be
debuggable or profileable. `-g` = DWARF call graphs (needs unstripped libs);
`--call-graph fp` is cheaper on arm64.

## Memory & jank

```bash
adb shell am dumpheap com.example.myapp /data/local/tmp/heap.hprof
adb pull /data/local/tmp/heap.hprof
hprof-conv heap.hprof heap-std.hprof     # Android→JVM hprof for MAT (Studio opens raw)

adb shell dumpsys gfxinfo com.example.myapp framestats  # 120-frame ns timestamps:
#   duration = FRAME_COMPLETED - INTENDED_VSYNC; aggregate section has janky-% and P50/90/95/99
adb shell dumpsys gfxinfo com.example.myapp reset       # between runs
```

LeakCanary remains the standard for automatic Activity/Fragment/ViewModel leak
detection in debug builds (`leakcanary-android-instrumentation` for CI).
`dumpsys meminfo` interpretation: see android-tools `references/debugging.md`.

## Production field data

`ApplicationExitInfo` (API 30+) on next launch:
`activityManager.getHistoricalProcessExitReasons(...)` — `REASON_ANR` entries
expose `getTraceInputStream()` (this is what Crashlytics/Sentry use). Fleet
level: Play Console Vitals (ANR bad-behavior threshold 0.47%) via the Play
Developer Reporting API.
