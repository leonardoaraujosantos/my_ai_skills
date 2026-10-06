---
name: mobile-profiling
description: Profile native mobile apps from the CLI - iOS Instruments via xcrun xctrace (Time Profiler, Allocations, Hangs, App Launch, SwiftUI), leaks/heap/vmmap against simulator processes, os_signpost custom timing, MetricKit field data; Android Perfetto system traces with trace_processor SQL, Macrobenchmark startup/frame metrics, Baseline Profiles, simpleperf CPU profiling, heap dumps and gfxinfo jank stats. Use when the user says "profile this app", "why is startup slow", "find the memory leak", "measure jank/frame drops", "record a trace", or "CPU/memory profiling on device".
argument-hint: [ios|android] [cpu|memory|startup|jank]
---

# Mobile Profiling Skill

CLI-driven profiling for native apps. Verified July 2026 (Xcode 26 /
Instruments 26, Perfetto current).

- `references/ios-instruments.md` — xctrace record/export, template guide,
  memory CLI tools, os_signpost, MetricKit, launch profiling
- `references/android-perfetto.md` — Perfetto configs & trace_processor SQL,
  Macrobenchmark, Baseline Profiles, simpleperf, heap/jank tooling

## Which tool answers which question

| Question | iOS | Android |
|----------|-----|---------|
| CPU hotspots | `xctrace record --template 'Time Profiler'` | simpleperf `app_profiler.py` |
| Slow startup | App Launch template | Macrobenchmark `StartupTimingMetric` + Baseline Profiles |
| Memory leak | Leaks template; `leaks <pid>` (simulator) | LeakCanary (debug builds); `am dumpheap` |
| Heap growth | Allocations template; `heap <pid>` (simulator) | `dumpsys meminfo` trend; heap dumps |
| Jank / dropped frames | Animation Hitches (device only) | `dumpsys gfxinfo framestats`; Macrobenchmark `FrameTimingMetric`; Perfetto frametimeline |
| UI hangs | Hangs *instrument* (bundled in Time Profiler) | Perfetto + ANR traces (see android-tools) |
| Custom timing you can assert on in CI | os_signpost intervals → `xctrace export` XPath | `TraceSectionMetric` / trace_processor SQL |
| Production field data | MetricKit (`MXMetricPayload` hang rate, launch times) | Play Vitals / Play Developer Reporting API; `ApplicationExitInfo` |
| Whole-system scheduling | System Trace template | Perfetto `record_android_trace` |

## Hard constraints (check before recommending a workflow)

- **iOS simulator vs device**: `leaks`/`heap`/`vmmap` work only against
  simulator processes (they're host processes). Animation Hitches, App Launch,
  Power Profiler, Processor Trace, and MetricKit need **real hardware**.
  Processor Trace additionally needs M4/A18+ silicon.
- **Android benchmarks need real devices**, a `<profileable
  android:shell="true"/>` release-like build, and an unlocked screen.
  Debuggable builds and emulators self-report as invalid results.
- **Instruments' aggregated call tree is not exportable** — `xctrace export`
  gives raw samples you aggregate yourself; plan for the XML `id=`/`ref=`
  dedup scheme.
- The two reliable "assertable numbers" pipelines for CI:
  iOS = os_signpost intervals via xctrace XPath export;
  Android = Macrobenchmark JSON + trace_processor SQL over Perfetto traces.

## Fastest useful commands

```bash
# iOS: 30-second CPU profile of a running app on a device
xcrun xctrace record --template 'Time Profiler' --device <UDID> \
  --attach MyApp --output app.trace --time-limit 30s

# iOS: leak scan of a simulator app right now
leaks MyApp   # by process name; SIMCTL_CHILD_MallocStackLogging=1 at launch for stacks

# Android: 30-second system trace, auto-pulled and opened
./record_android_trace -o trace.perfetto-trace -t 30s -b 64mb \
  sched freq gfx view am wm binder_driver

# Android: jank snapshot
adb shell dumpsys gfxinfo com.example.app framestats
```
