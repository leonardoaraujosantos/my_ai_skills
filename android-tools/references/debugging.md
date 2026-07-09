# Android Crash / ANR / Performance Debugging

## ANRs

Traces land in `/data/anr/` — not world-readable on unrooted production devices.

```bash
# Emulator (google_apis image) / rooted device — direct pull
adb root && adb pull /data/anr/ ./anr/

# Unrooted — always works
adb bugreport bugreport.zip
unzip -l bugreport.zip | grep anr            # traces at FS/data/anr/*
unzip -p bugreport.zip "FS/data/anr/anr_*" | less
```

Reading an ANR trace:
- Jump to the `"main"` thread block — its stack is what was blocked.
- `held by thread N` lines expose lock contention; find thread N's stack.
- In the big `bugreport-*.txt`, search `ANR in`, `VM TRACES AT LAST ANR`.
- The reason (Input dispatching timed out / Broadcast of Intent / executing
  service) is in `adb logcat -b events -d | grep am_anr`.

## Native crashes / tombstones

```bash
adb logcat -b crash -d                    # abort message + partial backtrace
adb bugreport bug.zip                     # tombstones at FS/data/tombstones/
adb root && adb pull /data/tombstones/ .  # emulator/rooted direct

# Symbolicate with UNSTRIPPED .so files:
ndk-stack -sym app/build/intermediates/merged_native_libs/debug/out/lib/arm64-v8a \
          -dump tombstone_00
adb logcat | ndk-stack -sym <path-to-unstripped-libs>    # live
```

Release builds: keep native symbols with
`android.buildTypes.release.ndk.debugSymbolLevel = "FULL"` (uploaded to Play,
also usable locally). Per-address alternative: `llvm-symbolizer` / `addr2line`
from the NDK toolchain.

## StrictMode

Violations log under tag `StrictMode`. System-wide without code changes:

```bash
adb shell setprop persist.sys.strictmode.visual 1    # red border flash on violation
adb shell setprop persist.sys.strictmode.disable 0
```

## dumpsys essentials

| Question | Command |
|----------|---------|
| What activity is on top? | `adb shell dumpsys activity activities \| grep -A3 mResumedActivity` |
| View hierarchy + fragments | `adb shell dumpsys activity top` |
| Memory breakdown (PSS) | `adb shell dumpsys meminfo com.example.app` — rising Activities/Views counts = leak smell |
| Jank / frame timings | `adb shell dumpsys gfxinfo com.example.app framestats` (reset with `... gfxinfo <pkg> reset`) |
| Battery: wakelocks/jobs/radio | `adb shell dumpsys batterystats --charged com.example.app` (reset: `--reset`) |
| Permissions/components/versionCode | `adb shell dumpsys package com.example.app` |
| Scheduled jobs / alarms | `adb shell dumpsys jobscheduler \| grep <pkg>` · `dumpsys alarm \| grep -A2 <pkg>` |
| Force Doze (test deferrals) | `adb shell cmd deviceidle force-idle` (undo: `unforce`) |

## Interpreting meminfo

PSS = proportional share of shared pages (the number that matters for
system-wide accounting); RSS = all resident pages (double-counts shared). Watch
`TOTAL PSS`, the `Activities` and `Views` object counts (should return to
baseline after closing screens — monotonic growth = leaked context), and
`Graphics` (texture/surface bloat). `dumpsys meminfo -a <pkg>` adds per-heap
detail. For real leak work use LeakCanary in debug builds; for heap dumps see
the mobile-profiling skill.
