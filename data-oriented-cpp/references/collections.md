# Collections and data representation

Reference implementations: `source/blender/blenlib/BLI_*.hh` in the Blender source.

---

## Compressed index sets (`IndexMask`)

### The representation

An index set is stored as a list of **segments**. Each segment covers a 16384-index window and
stores its members as `int16` offsets into that window. The constant is chosen deliberately:

- 8-bit offsets would make segments too small — per-segment bookkeeping would dominate.
- The top bit is unused so signed arithmetic works without sign-mixing bugs.
- The second-from-top bit is unused so `max_segment_size` itself fits in an `int16`.
- A power of two makes constructing a mask from a contiguous range near-free.

A fully-dense mask over 10M elements costs ~610 segment records, not 10M integers.

### Construction — prefer these over hand-rolled filter loops

```
IndexMask::from_indices(Span<T>, memory)
IndexMask::from_bits(BitSpan, memory)              // and the (universe, bits) overload
IndexMask::from_bools(Span<bool>, memory)          // and from_bools_inverse
IndexMask::from_predicate(universe, grain, memory, fn)
IndexMask::from_batch_predicate(...)               // predicate over a whole segment at once
IndexMask::from_ranges(OffsetIndices<T>, mask, memory)
IndexMask::from_every_nth(n, ...)
IndexMask::from_repeating(mask, ...)
IndexMask::from_group_ids(VArray<int>, ...)        // returns one mask per distinct id
IndexMask::from_union / from_intersection / from_difference
```

`IndexMaskMemory` is a linear allocator that owns the segment storage. A mask is a *view*; the
memory object must outlive it. This is the one ergonomic tax of the design — accept it, don't
wrap it in a self-owning type or you lose the cheap-slicing property.

### Iteration

```cpp
mask.foreach_index([&](const int64_t i) { ... });                  // by index
mask.foreach_index([&](const int64_t i, const int64_t pos) { ... }); // pos == position in mask
mask.foreach_index(fn, exec_mode::grain_size(1));                  // parallel
mask.foreach_index_optimized<int>(fn);                             // separate loops for range vs
                                                                   // non-range segments; more code
mask.foreach_segment([&](IndexMaskSegment seg) { ... });           // contiguous run at a time
IndexMask::foreach_segment_zipped({a, b}, fn);                     // co-iterate equal-size masks
```

Rules of thumb:

- `foreach_index` is the default.
- `foreach_index_optimized` only when the per-element body is tiny (a copy, a multiply). It
  generates a separate loop for range-shaped segments; on a large body that is pure binary bloat.
- `foreach_segment` when the kernel can vectorize over a run.
- `foreach_segment_zipped` instead of building an index-to-index map when walking two masks.

### Set algebra as an expression tree

`BLI_index_mask_expression.hh` builds a `Union / Intersection / Difference / Atomic` tree via
`ExprBuilder` and evaluates it in one pass. Use it instead of chaining pairwise `from_union` calls,
which materializes an intermediate mask per operation.

### Migration advice

Adopt top-down. Convert the outermost API to take `const IndexMask &`, then push it inward. A
mask that gets converted to `Vector<int>` two frames down has cost you memory and bought nothing.

---

## Virtual arrays (`VArray<T>`, `GVArray`)

### What it is

An interface over "a sequence of N values of type T" that does not commit to storage. Concrete
backings:

```cpp
VArray<float>::from_span(span)          // contiguous memory
VArray<float>::from_single(v, n)        // one value, N times — costs nothing
VArray<float>::from_func(n, fn)         // computed on demand
VArray<float>::from_derived_span<S, &S::field>(structs)   // strided field of an AoS array
VArray<float>::from_container(vec)
```

The point is caller convenience: a function taking `VArray` can be called with a constant without
the caller allocating N copies of it. This matters enormously in node/expression systems where most
inputs are constants.

### The `CommonVArrayInfo` trick

Naively, checking "is this a span?" plus "get the span" plus "is it a single value?" is three
virtual calls. `common_info()` returns all of it in **one** virtual call:

```cpp
struct CommonVArrayInfo {
  enum class Type : uint8_t { Any, Span, Single };
  Type type;
  bool may_have_ownership;   // true if data dangles when the varray dies
  const void *data;
};
```

Design lesson beyond varrays: when a hot path needs several facts about an object through an
interface, return a small POD holding all of them rather than adding N accessors.

### Bulk access beats element access

```cpp
varray.materialize(mask, dst_span);              // fill dst at mask positions
varray.materialize_compressed(mask, dst_span);   // fill dst densely, 0..mask.size()
varray.get_internal_span();                      // only after is_span()
varray.get_internal_single();                    // only after is_single()
```

If you find yourself calling `varray.get(i)` in a loop, you have chosen the wrong API. Either
materialize once or devirtualize.

### Devirtualization — and its cost

```cpp
devirtualize_varray(src, [&](const auto src) { /* src is a concrete type here */ });
devirtualize_varray2(a, b, [&](const auto a, const auto b) { ... });
```

Each devirtualized parameter multiplies the number of instantiated loop bodies. Two parameters with
two shapes each is four bodies; three is eight. Blender's own header calls out "exponentially
increasing compile times and binary sizes" and instructs benchmarking each case.

**Practical policy:** devirtualize zero parameters by default. Devirtualize one when profiling shows
virtual-call overhead is a measurable fraction of a hot kernel. Devirtualize two only for the
smallest bodies (a single arithmetic op). Never three without numbers in the commit message.

---

## Implicit sharing (COW done properly)

### The control block

```cpp
class ImplicitSharingInfo {
  mutable std::atomic<int>     strong_users_ = 1;  // 0 = expired, 1 = mutable, >1 = shared/immutable
  mutable std::atomic<int>     weak_users_   = 1;  // observers that don't keep the data alive
  mutable std::atomic<int64_t> version_      = 0;  // bumped by tag_ensured_mutable()
  virtual void delete_self_with_data() = 0;        // knows how the data was allocated
};
```

`version()` reads it; `tag_ensured_mutable()` increments it and is called from the make-mutable
path — so "about to be modified" and "version bumped" are the same event by construction, and
nobody has to remember to bump it.

Two deployment shapes:

- **Separate** from the data, for plain arrays — the classic `{T *data; const ImplicitSharingInfo *sharing_info;}`
  pair you will see all over Blender's DNA structs.
- **Embedded** in a class via `ImplicitSharingMixin`, when the shared thing is an object.

Note the control block knows *how to free* the data. This is the detail that lets a generic sharing
mechanism coexist with several allocators.

### The API you actually call

```cpp
implicit_sharing::copy_shared_pointer(src, src_info, &dst, &dst_info);  // cheap "copy"
implicit_sharing::free_shared_data(&data, &info);
implicit_sharing::make_trivial_data_mutable(&data, &info, size);        // COW happens here
implicit_sharing::resize_trivial_array(&data, &info, old_n, new_n);
implicit_sharing::info_for_mem_free(data);                              // adopt existing memory
```

The mutation path is always: **call `make_*_mutable` before writing.** If the count is 1 it is a
no-op; if it is greater it copies and decrements. There is no way to accidentally write shared
data if this is the only write path.

### Why the version counter earns its keep

`weak_users_` plus `version_` lets an observer hold a cheap handle and answer "did this change since
I last looked?" without keeping the data alive and without the owner knowing observers exist. Every
codebase that omits this reinvents it as ad-hoc dirty flags in five different classes.

### Shared caches

`SharedCache<T>` puts a lazily computed value behind a shared pointer, so an original and its
evaluated copy share not just the input data but the *derived* result:

- Compute bounds on either object → available on both.
- Mutate either → the cache un-shares, and they stop influencing each other.

The canonical win: in a copy-on-evaluation loop, an expensive derived value is computed on the first
evaluation and never again for as long as nothing invalidates it, even though a fresh evaluated copy
is made each time.

---

## CSR grouping (`OffsetIndices<T>`)

```cpp
OffsetIndices<int> faces(offsets_span);   // offsets.size() == groups + 1
IndexRange group = faces[i];              // -> offsets[i] .. offsets[i+1]
IndexRange span  = faces[IndexRange(a,b)];
int total        = faces.total_size();
OffsetIndices sub = faces.slice(range);
```

Helpers that exist so you don't hand-roll the prefix sum:

```cpp
offset_indices::accumulate_counts_to_offsets(counts_to_offsets);          // in-place exclusive scan
offset_indices::accumulate_counts_to_offsets_with_overflow_check(...);    // returns optional
offset_indices::gather_group_sizes(offsets, mask, r_sizes);
offset_indices::sum_group_sizes(offsets, mask);
offset_indices::build_reverse_offsets(indices, r_offsets);                // build the map-back
offset_indices::gather_selected_offsets(src_offsets, mask, r_offsets);
```

`GroupedSpan<T>` bundles `OffsetIndices` with the flat data array so a single parameter carries
both.

The construction idiom is always the same and worth memorizing:

1. allocate `Array<int> offsets(groups + 1)`
2. write each group's **count** into `offsets[i]`
3. `accumulate_counts_to_offsets(offsets)` — turns counts into offsets in place
4. allocate the flat data array of `offsets.last()` elements
5. fill it, in parallel, using `offsets[i]` as each group's write cursor

Step 5 is embarrassingly parallel precisely because the offsets are known before any data is
written. This is why the count-then-scan-then-fill shape keeps showing up.

**Debug-build caveat:** the constructor asserts the offsets are sorted, which is O(n) per
construction and can make debug builds unusable on large data. Blender added a `NoSortCheck`
tag overload for hot paths. If you copy the pattern, copy the escape hatch too.

---

## Runtime type erasure (`CPPType`, `Any`, generic containers)

When a system must handle types decided at runtime (node sockets, attributes, serialized values),
the choice is between templates everywhere (compile-time explosion) and `void*` plus manual
bookkeeping (unsound). `CPPType` is the middle path: a singleton per type carrying function
pointers for construct / destruct / copy / move / fill / compare / hash, plus size and alignment.

Generic counterparts to the typed containers then exist and are named consistently:
`GSpan`, `GMutableSpan`, `GArray`, `GVArray`, `GVMutableArray`, `GVectorArray`, `GPointer`.

Convert to typed at the earliest point you know the type — `gvarray.typed<float>()` — and stay typed
from there. The generic layer is a boundary, not a way of life.

---

## Attribute layers — the pattern above raw arrays

When elements live on several **domains** (points, edges, faces, corners, instances) and carry a
user-extensible set of named fields, the right abstraction is an **attribute accessor**, not a
struct with a growing list of members:

```cpp
GAttributeReader r = attributes.lookup("position");
VArray<float3>   p = attributes.lookup<float3>("position", AttrDomain::Point);
VArray<float>    w = attributes.lookup_or_default<float>("weight", AttrDomain::Point, 1.0f);
GVArray adapted    = attributes.adapt_domain(varray, AttrDomain::Face, AttrDomain::Point);
attributes.foreach_attribute([&](const AttributeIter &it) { ... });
attributes.add(name, domain, type, initializer);
GSpanAttributeWriter w2 = attributes.lookup_for_write_span(name);
```

Three things to steal even if you never build a mesh:

- **Domain adaptation as a first-class operation.** Interpolating face data to points is a named
  API call, not something each consumer open-codes.
- **Lookup-or-default.** Absent attributes behave as a constant virtual array. Consumers never
  branch on existence.
- **Anonymous attributes.** Intermediate results get generated, prefixed names (Blender uses `.a_`)
  and their lifetime is tracked by a reference set, so they are dropped automatically when nothing
  downstream needs them. This is garbage collection for intermediate columns, and it is what makes
  a node-graph system not leak state.

A separate `AttributeFilter` object decides propagation policy (which attributes survive an
operation). Making that an explicit, passed-in policy rather than a hardcoded rule inside each
operation is what keeps forty operations consistent.
