# iOS Profiling — Instruments via xctrace (Xcode 26)

## Record

```bash
xcrun xctrace list templates          # discover (names below verified on 26.0)
xcrun xctrace list devices            # devices + simulators with UDIDs

# Launch and profile
xcrun xctrace record --template 'Time Profiler' --device <UDID> \
  --launch -- com.example.MyApp --output app.trace --time-limit 30s

# Attach to a running process
xcrun xctrace record --template 'Time Profiler' --attach <pid|name> --output app.trace

# Whole system
xcrun xctrace record --template 'System Trace' --all-processes --time-limit 10s

# Extra instruments / env vars
xcrun xctrace record --template 'Time Profiler' --instrument 'Hangs' \
  --env MY_FLAG=1 --launch -- MyApp.app
```

Useful flags: `--window <dur>` (ring-buffer tail capture), `--append-run`,
`--no-prompt` (skip privacy prompts — needed for automation), `--target-stdout -`.
Omit `--device` for the host Mac; simulators addressed like devices. Stop an
unbounded recording with SIGINT.

## Template guide

| Template | Use for |
|----------|---------|
| Time Profiler | CPU sampling + thread states; **includes the Hangs instrument** (>250 ms) |
| CPU Profiler | CPU-clock-driven sampling (less waker bias) |
| Allocations / Leaks | Heap growth / periodic leak snapshots |
| App Launch | Cold-launch phases incl. pre-main dyld work (`DYLD_PRINT_STATISTICS` is dead) |
| Animation Hitches | Frame delivery vs deadline (device only) |
| SwiftUI | Rebuilt in Instruments 26: Update Groups lane + cause→effect graph for view updates |
| Data Persistence | Core Data + SQLite (this is the current name of the old "Core Data" template) |
| Network | HTTP; exportable as HAR: `xctrace export --har` |
| Swift Concurrency | Task/actor contention |
| Power Profiler | On-device power rails (new in 26) |
| Processor Trace | Exact instruction-level trace — M4/A18+ only, short sessions |

**There is no "Hangs" template** — it's an instrument; add with
`--instrument 'Hangs'` or use Time Profiler which bundles it.

## Export (programmatic)

```bash
xcrun xctrace export --input app.trace --toc          # discover table schemas
xcrun xctrace export --input app.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]'
```

Gotchas that break parsers:
- Output XML uses **reference dedup**: first occurrence carries `id="N"`, later
  rows use `<backtrace ref="N"/>` — build an id→value map while streaming.
- Values carry raw + formatted forms: `<weight fmt="1.00 ms">1000000</weight>`.
- You get **raw samples, not the aggregated call tree** — fold stacks yourself
  (Brendan Gregg format) for flame graphs; the Instruments flame-graph view is
  UI-only.
- Useful schemas in a Time Profiler trace: `time-profile`, `hang-risks`,
  `potential-hangs`, `os-signpost`, `dyld-library-load`, `thread-info`.

## Memory CLI (simulator processes only)

Simulator apps are host processes, so `/usr/bin/{leaks,heap,vmmap,malloc_history}`
work directly:

```bash
SIMCTL_CHILD_MallocStackLogging=1 xcrun simctl launch booted com.example.MyApp
leaks MyApp --outputGraph=out.memgraph     # leak scan (works on .memgraph too)
heap <pid>                                  # heap composition by class
vmmap --summary <pid>                       # VM region breakdown
malloc_history <pid> --fullStacks <addr>    # needs MallocStackLogging
```

On physical devices these don't work — use Allocations/Leaks templates over
xctrace.

## os_signpost (the CI-assertable channel)

```swift
let log = OSLog(subsystem: "com.example.app", category: .pointsOfInterest)
os_signpost(.begin, log: log, name: "RefreshFeed", signpostID: id)
os_signpost(.end,   log: log, name: "RefreshFeed", signpostID: id)
// modern: OSSignposter.beginInterval/endInterval
```

Recorded by Time Profiler (verified `os-signpost` table in the TOC); extract:

```bash
xcrun xctrace export --input app.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="os-signpost"]'
```

## MetricKit (production field data)

`MXMetricManager.shared.add(subscriber)`;
`didReceive([MXMetricPayload])` = daily aggregates — launch-time histograms
(`timeToFirstDraw`), **hang rate** (`histogrammedApplicationHangTime`),
CPU/memory/exit metrics. `didReceive([MXDiagnosticPayload])` = crash/hang/CPU-
exception diagnostics with `callStackTree` (UUIDs + offsets — symbolicate
offline with atos), delivered immediately on iOS 15+. `jsonRepresentation()`
ships to your backend. **Not delivered on simulator or under the debugger**;
Xcode Organizer shows the aggregate but has no CLI export.

## Launch-time levers

Profile with the App Launch template, then: fewer dylibs (static linking /
mergeable libraries), fewer static initializers and `+load` methods, chained
fixups (default on modern targets).
