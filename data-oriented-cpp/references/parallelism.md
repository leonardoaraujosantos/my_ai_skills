# Parallelism without locks

Reference implementations: `BLI_task.hh`, `BLI_lazy_threading.hh`, `BLI_cache_mutex.hh`,
`BLI_enumerable_thread_specific.hh`, `BKE_paint_bvh.hh`.

---

## 1. Ownership partition — the only scalable answer to shared elements

### The problem

Split a mesh into spatial chunks and process them in parallel. A vertex on a chunk boundary is used
by faces in two chunks. Two threads want to write it. The usual answers:

- per-element mutex — memory blowup, contention, cache-line ping-pong
- atomics — only works for commutative updates, and is slow
- a serial fixup pass — kills the speedup
- ignore it — a race you will hit in production and not in tests

### The pattern

Decide ownership **once, when you build the partition**. Each chunk stores its element indices in
one array, ordered so that **owned elements come first**:

```cpp
struct MeshNode {
  LocalVertMap vert_indices_;   // owned first, then shared-with-other-nodes
  int unique_verts_num_ = 0;

  Span<int> verts()     const;  // first unique_verts_num_ — SAFE TO WRITE in parallel
  Span<int> all_verts() const;  // everything the node touches — READ ONLY
};
```

An element that appears in two chunks is "owned" by exactly one of them and appears in the shared
tail of the other. Parallel chunk processing then has a provably disjoint write set. No locks
anywhere.

Note the storage detail: the index array doubles as a `VectorSet`, so it is also a global-index →
local-index map, with `int16` slot indices because a chunk never holds more than 2^15 elements.
Two jobs, one allocation.

### The rule to carry away

**Every parallel unit of work must have a write set you can name and prove disjoint.** If you
cannot state it in one sentence, the design is not parallel yet. Ownership partition, index-range
partition, and per-thread accumulation-then-merge are the three ways to get there. Locks are what
you use when you have failed to.

---

## 2. Thread-local scratch

```cpp
struct LocalData {
  Vector<float3> positions;
  Vector<float>  factors;
  Vector<float>  distances;
  Vector<float3> translations;
};

threading::EnumerableThreadSpecific<LocalData> all_tls;

node_mask.foreach_index(
    [&](const int i) {
      LocalData &tls = all_tls.local();
      tls.factors.resize(nodes[i].verts().size());   // capacity stabilizes after a few chunks
      tls.translations.resize(nodes[i].verts().size());
      compute(nodes[i], tls);
    },
    exec_mode::grain_size(1));
```

Points that are easy to get wrong:

- **`resize`, never `clear()` + `reserve()` + push_back.** The whole point is reusing capacity.
- **Construct the `EnumerableThreadSpecific` outside the parallel region**, and anything expensive
  the kernel needs (attribute readers, matrices, accessors) outside too. Building a reader per
  chunk is the most common way this pattern gets silently ruined.
- `grain_size(1)` is right when each chunk is already a substantial unit of work. It is wrong for
  per-element loops.
- Blender's wrapper falls back to a thread-id-keyed map when built without TBB. If you write your
  own, keep the same shape so the fallback is not a different API.

---

## 3. Lazy threading — for tasks of unknown, heterogeneous cost

### Why grain size is not enough

`parallel_for` with a grain size assumes tasks are roughly equal-cost. Two situations break it:

- tasks differ wildly in cost
- cost is not predictable before running the task

Schedule individually and the cheap tasks drown in overhead. Batch them and one expensive task
stalls its whole batch while other threads idle. There is no grain size that is right.

### The mechanism

Default to a single thread. When a task discovers mid-execution that it is about to do something
slow, it calls:

```cpp
lazy_threading::send_hint();
```

A `HintReceiver` further up the stack catches this and releases the sibling tasks that were queued
on this thread, letting idle threads steal them. Net effect:

- all-cheap workload → zero threading overhead, best cache behaviour
- one expensive task → the rest move off that thread and run concurrently

**The earlier a task can send the hint, the better** — ideally the moment it decides which branch it
is taking, before doing the work. A hint sent at the end is useless.

Wire the receiver where you own the task pool:

```cpp
auto fn = [&]() { /* release queued siblings */ };   // must outlive the receiver
lazy_threading::HintReceiver receiver{fn};
```

(The header explicitly warns not to pass a temporary lambda into the constructor — store it in a
named variable first.)

---

## 4. Two throttles worth stealing verbatim

### Bandwidth-bound work

```cpp
threading::memory_bandwidth_bound_task(approximate_bytes_touched, [&]() {
  /* mostly memcpy / fill / gather over huge buffers */
});
```

Below roughly L3 size (Blender uses 8 MB as the cutoff) it just runs the function — cache bandwidth
is plentiful. Above it, thread count is capped, because past a few threads you saturate the memory
controller and additional threads only add contention.

Counterintuitive and frequently missed: **for memcpy-shaped work, more threads make it slower.**

### Explicit thread caps

```cpp
threading::max_threads_task(n, fn);
```

For work that contends on a shared resource (a device queue, a file, a fixed-size pool) where the
right parallelism is a property of the resource, not the CPU.

---

## 5. Lazy caches under threading

### The two bugs a raw mutex gives you

1. **The double-checked-lock bug** — everyone rewrites it, most get the memory ordering wrong.
2. **The work-stealing re-entrancy deadlock** — thread A takes the lock and runs the compute
   function; the compute function uses `parallel_for`; the scheduler steals an unrelated task onto
   thread A; that task also wants this cache; thread A blocks on a lock it holds. Deadlock, on a
   machine with idle cores, reproducible only under load.

Bug 2 is why `isolate_task` exists and why any lazy cache in a work-stealing environment must run
its compute function isolated.

### The primitive

```cpp
class CacheMutex {
  Mutex mutex_;
  std::atomic<bool> cache_valid_ = false;
 public:
  void ensure(FunctionRef<void()> compute_cache) {
    if (cache_valid_.load(std::memory_order_acquire)) return;   // fast path
    this->ensure_impl(compute_cache);                           // locks + isolates + stores release
  }
  void tag_dirty();
  bool is_cached() const;
};
```

Usage — mutex and the data it guards sit adjacent, both `mutable`:

```cpp
class Mesh {
  mutable CacheMutex bounds_cache_mutex_;
  mutable Bounds<float3> bounds_cache_;
 public:
  const Bounds<float3> &bounds() const {
    bounds_cache_mutex_.ensure([&]() { bounds_cache_ = compute_bounds(); });
    return bounds_cache_;
  }
};
```

Design decisions worth copying:

- **One mutex per cache, not one per class.** More memory, far less contention, and invalidating one
  cache does not invalidate the others.
- **The mutex does not own the data.** Keeps it a small, embeddable primitive.
- **`ensure` is idempotent and callable from any thread** — but every caller must pass an equivalent
  compute function. Document that.

For caches that should survive copy-on-evaluation, use the sharing-aware variant described in
`collections.md` under "Shared caches".

---

## 6. Task size hints

When tasks genuinely have different sizes and you *can* measure them cheaply, tell the scheduler
instead of guessing a grain size:

```
TaskSizeHints::Type::Static             // all equal — plain grain size is fine
TaskSizeHints::Type::IndividualLookup   // size known per task, looked up one at a time
TaskSizeHints::Type::AccumulatedLookup  // size of a consecutive range known in O(1)
                                        // (i.e. you already have a prefix sum — see OffsetIndices)
```

`AccumulatedLookup` is the interesting one: if your groups are already stored as CSR offsets, the
scheduler can binary-search the offsets array to split work into equal-*cost* rather than
equal-*count* batches, for free. This is a concrete payoff from choosing the offset representation
in the first place.

---

## 7. Profiling hygiene

Two habits from Blender's brush kernels that cost nothing and save hours:

- **`BLI_NOINLINE` on kernel helper functions.** Aggressive inlining smears a hot loop across the
  caller and the profile becomes unreadable. Marking the pipeline stages noinline gives you a
  per-stage cost breakdown. Remove it only if a stage proves to be inline-critical.
- **A scoped profiler macro at the top of each stage** (`PRF_scope(Category)`), compiled out in
  release. Named stages mean the profile matches the mental model of the pipeline.

Both are about making the profile *legible*, which matters more than making it *complete*.
