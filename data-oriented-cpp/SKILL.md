---
name: data-oriented-cpp
description: Design and review performance-critical C++ that processes large homogeneous datasets - geometry, entities, particles, simulation state, image/array pipelines, ECS-style systems. Encodes patterns proven at scale in Blender's blenlib/nodes/transform/depsgraph - compressed index sets instead of index vectors, virtual arrays with call-site devirtualization, implicit sharing (COW plus a version counter), CSR offset grouping, lock-free parallel writes via ownership partition, lazy threading for unknown-size tasks, normalize-then-operate for N types x M operations, granular invalidate-and-flush dependency tracking, and self-describing serialization that survives schema change. Use when writing or reviewing hot-loop C++ over big arrays, choosing a parallelization strategy, designing an editor or engine subsystem, adding undo/persistence, or whenever a design has N data types multiplied by M operations. Triggers - "hot loop", "millions of elements", "SoA vs AoS", "cache locality", "copy-on-write", "selection mask", "parallel_for", "grain size", "data race on shared vertices", "undo system", "file format versioning", "this switch statement has 20 cases".
argument-hint: [design|review|parallelize|persist] [what]
---

# Data-Oriented C++

Patterns for C++ that touches **large arrays of similar things** and must stay fast, correct under
threading, and maintainable for a decade. Every rule here is drawn from a system that actually
survived that: Blender's `blenlib`, `functions`/`nodes`, `editors/transform`, `depsgraph`, and
`blenloader`. `references/blender-map.md` gives exact file paths to read the originals.

## Scope check — read this first

These patterns buy throughput and long-term flexibility at the cost of indirection. They pay off
when **N is large and the elements are homogeneous**. They are a net loss on small-N code, on
one-shot scripts, and on business logic where clarity dominates.

Apply when: N routinely exceeds ~10k, the same operation runs over every element, the data
outlives one function call, or several subsystems must agree on one representation.
Otherwise write the plain loop and move on. Say so explicitly rather than reaching for machinery.

---

## Part 1 — Represent the data

### 1. Pass a selection, not a filtered copy

The default instinct is `Vector<int> selected` or, worse, copying the selected elements into a new
array. Both are wrong at scale: the vector costs 8 bytes per element and loses the fact that
selections are overwhelmingly *runs* of consecutive indices.

Use a **compressed index set**: segment the index space, store within-segment offsets as `int16`,
and expose iteration through `foreach_index` rather than an iterator. Blender's `IndexMask` uses
16384-element segments — small enough that `int16` suffices, large enough that per-segment overhead
vanishes. A selection of "every element" costs O(number of segments), not O(N).

Consequences that matter more than the memory win:

- Build masks with set algebra (`from_union`, `from_difference`, `from_predicate`, `from_bools`)
  instead of hand-rolled filter loops.
- Thread the mask through **every** layer of the API. If a function takes an array it should take a
  mask too. Half-adoption is worse than none, because you pay conversion at every boundary.
- Segment-wise iteration (`foreach_segment`) lets a kernel process a contiguous run at a time,
  which is where SIMD and prefetching live.

Details and the full API in `references/collections.md`.

### 2. Take a virtual array at the boundary; devirtualize inside the hot loop

A function that takes `Span<float>` forces every caller to materialize an array — even the caller
who has a single constant value, or a value computed on demand, or a differently-strided source.
A function that takes a **virtual array** accepts all of those.

The cost is a virtual call per element, which is fatal in a tight loop. The fix is not to abandon
the abstraction but to **re-specialize at the call site**: inspect the runtime shape (is it a span?
a single value?) and dispatch to a monomorphized loop.

```cpp
void scale(const VArray<float> &src, MutableSpan<float> dst, const IndexMask &mask) {
  devirtualize_varray(src, [&](const auto src) {          // src is now Span or SingleAsSpan
    mask.foreach_index_optimized<int>([&](const int64_t i) {
      dst[i] = src[i] * 2.0f;
    });
  });
}
```

**This trades compile time and binary size for run time, and the trade is exponential in the number
of devirtualized parameters.** Devirtualize one or two parameters in genuinely hot functions.
Benchmark before adding a third. Blender's own header says exactly this, and it is the single most
misapplied idea in this skill.

### 3. Share by default; copy on write; version for change detection

Do not choose between "copy everything" (safe, slow) and "share raw pointers" (fast, unsound).
Attach to each shared buffer a small control block holding an **atomic strong count, an atomic weak
count, and a version counter**:

- strong count `== 1` → the single owner may mutate in place.
- strong count `> 1` → immutable; a writer must copy first.
- weak count + version → an observer can ask "has this changed since I looked?" in O(1) without
  holding the data alive.

That third field is what people leave out and then rebuild badly as dirty flags scattered across
the codebase. Getting change detection for free is most of the value.

Corollary: a *cache derived from shared data can itself be shared*. If an evaluated copy and its
original share the input, they can share the computed bounds too — computing it on either makes it
available to both, and the cache un-shares the moment one of them is mutated.

### 4. Group with offsets, not with vector-of-vectors

For "N groups of variable-size runs" — faces to corners, curves to points, nodes to elements — do
not store `Vector<Vector<T>>` and do not store `(start, size)` pairs. Store a **sorted array of n+1
offsets** over one flat data array. Group `i` is `data[offsets[i] : offsets[i+1]]`.

Half the memory of start/size pairs, one allocation instead of N, perfectly cache-friendly, and the
extra trailing element exists specifically so group access needs no branch. Build it by writing
counts into the array and running an exclusive prefix sum in place.

This is CSR. Name it that in comments so the next reader recognizes it.

---

## Part 2 — Make it parallel without locks

### 5. Partition ownership so writes need no synchronization

The hard case is shared elements: a vertex used by faces in two different chunks, an entity
referenced by two systems. The lazy answer is a mutex or atomics per element. The right answer is
to **decide ownership once, at partition time**.

Blender's approach: each spatial node stores its element indices with the *owned* ones first, and
exposes two accessors — `verts()` (owned, safe to write) and `all_verts()` (everything the node
touches, read-only). Chunks then run fully in parallel with zero synchronization, because no two
chunks write the same element by construction.

Design rule: **every parallel unit of work must have a provably disjoint write set.** If you cannot
state what that set is, you do not yet have a parallel design — you have a race you haven't hit.

### 6. Thread-local scratch, resized rather than reallocated

Kernels that need temporaries should not allocate per element or per chunk. Declare a scratch
struct, hold one per thread, and `resize()` its vectors at the top of each chunk. After the first
few chunks the capacity has stabilized and allocation cost goes to zero.

```cpp
struct LocalData {
  Vector<float3> positions;
  Vector<float>  factors;
  Vector<float3> translations;
};
threading::EnumerableThreadSpecific<LocalData> all_tls;

mask.foreach_index([&](const int i) {
  LocalData &tls = all_tls.local();
  tls.factors.resize(chunk_size(i));   // amortizes to zero
  ...
}, exec_mode::grain_size(1));
```

### 7. Don't guess a grain size for heterogeneous work — send a hint

A grain size is the right tool only when tasks are roughly equal-cost. When per-task cost varies
wildly and is unknowable in advance, both options are bad: schedule individually and pay overhead
on the cheap tasks; batch and let one expensive task stall its whole batch.

The resolution is **lazy threading**: keep everything on one thread by default, and have a task
*notify the scheduler when it discovers it is about to be slow*, at which point sibling tasks are
released to other threads. Cheap workloads pay zero threading overhead; expensive ones parallelize.
The earlier a task can send the hint, the better.

Two related throttles worth stealing:

- **Bandwidth-bound throttling.** For work that is mostly memcpy over buffers far larger than L3,
  *cap* the thread count. Past a point more threads add contention and no bandwidth.
- **Task isolation.** Any lazy cache computed under a lock must run isolated, or a work-stealing
  scheduler can re-enter it on the same thread and deadlock. Wrap it once in a `CacheMutex`-style
  primitive instead of getting it right at each of forty call sites.

`references/parallelism.md` has both, with the failure modes spelled out.

---

## Part 3 — Structure the system

### 8. N data types x M operations → normalize, then operate once

When you find yourself facing "we need translate/rotate/scale for meshes, bones, keyframes, UVs,
curve handles, timeline strips, and node positions", **do not write M x N implementations and do not
write an abstract base class with M virtual methods per type.**

Convert every input type into one flat, uniform intermediate — Blender's `TransData` is a pointer to
the value, its initial value, a center, a to/from-global matrix pair, and flags — and then implement
each operation exactly once against that intermediate. Orthogonal features (constraints, snapping,
proportional falloff, numeric entry, mirroring) then compose on top and are automatically available
to every type.

Blender's transform system is 28 converters plus ~30 operations. The alternative was 840
implementations. **The test of a good intermediate is that adding a new data type requires writing
exactly one converter and touching nothing else.**

This is the highest-leverage pattern in this document. Reach for it whenever a switch statement
starts growing a case per type in more than one place.

### 9. Invalidate granularly; flush once; back up what re-evaluation destroys

For anything with derived state, three separate mechanisms — do not conflate them:

1. **Tagging** at the finest granularity you can afford (this property of this component of this
   object changed), not "something changed."
2. **Flushing** as a separate pass that propagates tags along the dependency graph before
   evaluation, so each consumer is visited once regardless of how many upstream things changed.
3. **Runtime backup/restore** for caches that live on the object being re-evaluated. When
   evaluation replaces an object with a fresh copy, expensive runtime-only state (GPU buffers,
   spatial indices, simulation state) must be explicitly saved and re-attached, per type. Blender
   has ten dedicated files for this. It is unglamorous and there is no generic shortcut.

For UI specifically: let consumers **subscribe to the address of the property they display**, so a
change notifies exactly the regions that care instead of triggering a global redraw.

### 10. Serialize the schema alongside the data

A binary format that hardcodes struct layout in the reader is dead the first time a field is added.
Instead, **write a machine-readable description of every struct into the file itself** — field
names, types, offsets. On load, match old fields to new ones by name and type and copy what
matches; new fields keep their defaults, removed fields are dropped. No per-field migration code for
the overwhelmingly common case of adding or removing a member.

Reserve explicit, per-version migration functions for *semantic* changes (units changed, one field
split into two, a default flipped). Keep one file per release, append-only, never edit an old one.

This is why Blender opens files from 2003. `references/persistence.md` covers it plus the undo
counterpart: content-defined chunking with deduplication, so an undo step stores only what changed.

---

## Reference map

| Need | Read |
|---|---|
| IndexMask, VArray, ImplicitSharing, OffsetIndices, type erasure, attribute layers | `references/collections.md` |
| Ownership partition, thread-local scratch, lazy threading, cache primitives, bandwidth throttling | `references/parallelism.md` |
| Normalize-then-operate, tagging/flush, plugin vtables, operator discipline, kernel fusion | `references/architecture.md` |
| Self-describing serialization, versioning discipline, dedup undo, per-chunk snapshots | `references/persistence.md` |
| Exact file paths in the Blender source for every pattern above | `references/blender-map.md` |

## Review checklist

Use this when reviewing rather than writing. Each smell has a specific fix above.

| Smell | Fix |
|---|---|
| `Vector<int>` of selected indices threaded through an API | Compressed index set (1) |
| A function overload per input shape (span / single / computed) | Virtual array at the boundary (2) |
| `devirtualize` on four or more parameters | Cut to one or two; benchmark (2) |
| Defensive deep copy "to be safe" | Implicit sharing with COW (3) |
| Dirty flags sprinkled across several classes | Version counter on the shared block (3) |
| `Vector<Vector<T>>` for variable-size groups | CSR offsets (4) |
| Mutex or atomic per element in a parallel loop | Ownership partition (5) |
| Allocation inside a per-chunk parallel loop | Thread-local scratch, resized (6) |
| A grain size constant chosen by feel | Measure, or use lazy threading if cost is unknowable (7) |
| Thread count scaled to core count for a memcpy-shaped loop | Bandwidth throttle (7) |
| Lazy cache behind a raw mutex in a work-stealing pool | Isolate the task (7) |
| A switch on type appearing in more than one file | Normalize to one intermediate (8) |
| Global "something changed, redraw everything" | Granular tag plus flush pass (9) |
| Reader that memcpy's a struct straight out of a file | Self-describing schema plus reconstruct (10) |
| Undo step that snapshots the whole document | Chunked dedup, or per-region snapshots (10) |

## Two honest caveats

- **Indirection has a floor cost.** Virtual arrays, masks, and accessors each add a layer. On small
  N they lose to a plain loop, sometimes badly. State the N you are designing for.
- **Half-adoption is the worst outcome.** These patterns compound — masks are cheap because *every*
  layer speaks masks. Introducing one into a codebase that converts at every boundary pays all the
  complexity and none of the speed. Either commit a subsystem or leave it alone.
