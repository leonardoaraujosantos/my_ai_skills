# System architecture patterns

Reference implementations: `source/blender/editors/transform/`, `source/blender/depsgraph/`,
`source/blender/bmesh/`, `source/blender/compositor/`, `source/blender/functions/`.

---

## 1. Normalize, then operate once (N types x M operations)

### The trigger

You have M operations that must work on N different data types, and the naive answer is M x N
implementations or an abstract base class with M virtual methods that every type must implement.

Concretely, Blender needed translate / rotate / scale / shear / bend / warp / push-pull / to-sphere
/ trackball / tilt / shrink-fatten / edge-slide / vert-slide / time-slide / mirror (~30) to work on
mesh vertices, edit-bones, pose bones, F-curve keyframes, NLA strips, UVs, curve control points and
handles, lattice points, metaball elements, mask splines, motion-tracking markers, grease pencil
points, VSE strips, node positions, particles, point clouds, and the 3D cursor (~28). That is 840
combinations.

### The structure

**One flat intermediate.** Every converter flattens its type into an array of:

```cpp
struct TransDataBasic {
  void  *extra;       // back-pointer to the real element
  float *loc;         // pointer to the live value being edited
  float  iloc[3];     // initial value, for cancel and for delta math
  float  center[3];   // this element's own center
  float *val;         // scalar channel for non-positional transforms
  float  ival;
  int    flag;
};

struct TransData : TransDataBasic {
  float dist, rdist, factor;   // proportional editing
  float mtx[3][3], smtx[3][3]; // to/from global space
  float axismtx[3][3];         // element's own orientation
  ...
};
```

The critical field is `float *loc` — a **pointer to the live data**, not a copy. Operations write
through it. Cancel restores from `iloc`. No write-back pass, no type knowledge in any operation.

**28 converters, ~30 operations, each written once.** Adding a new editable data type = write one
converter file. Adding a new operation = write one mode file, and it immediately works on all 28
types.

**Orthogonal features compose on the intermediate**, so each is also written once and applies
universally: constraints (axis/plane locking), custom orientations, snapping, proportional editing
with falloff curves, numeric input, mirroring, modal keymaps, gizmos.

### The test

**Adding a new data type must require writing exactly one converter and touching nothing else.**
If it requires editing the operations too, the intermediate is missing a field — fix the
intermediate, do not special-case the operation.

### When it does not apply

If the M operations genuinely need type-specific semantics (not just type-specific *access*), you
do not have a normalizable problem. The tell is whether the operations differ in *what they compute*
or only in *where the numbers live*. Only the latter normalizes.

---

## 2. Granular invalidation, separate flush, explicit runtime backup

Three distinct mechanisms. Conflating them is the usual failure.

### Tag at the finest granularity you can afford

Blender's dependency graph is three tiers: **ID node** (this object) → **component node**
(its transform / its geometry / its animation / its shading) → **operation node** (a specific step).
Tagging says "the geometry component of object X changed", not "something changed".

The payoff is not the tagging itself but everything downstream: a transform-only change does not
invalidate the geometry, so the mesh is not re-evaluated, so its GPU buffers survive.

### Flush as its own pass

Tags propagate along the graph in a **separate traversal before evaluation**. Each consumer is
visited once regardless of how many upstream things were tagged. Doing invalidation eagerly at each
tag site is O(tags x downstream) instead of O(graph).

### Back up runtime state across re-evaluation

Copy-on-evaluation replaces the object with a fresh copy. Anything expensive that lived on the old
object and is not derivable from the source data — GPU buffers, spatial acceleration structures,
simulation state, animation state, open file handles — is lost unless explicitly saved and
re-attached.

Blender has ten dedicated files for this (`intern/eval/deg_eval_runtime_backup_*.cc`), one per data
type: object, pose, animation, modifier, movieclip, scene, sequencer, sound, volume. There is no
generic shortcut, because "what is worth preserving" is a per-type judgment.

**This is the part everyone forgets, and it shows up as a mysterious performance cliff whenever an
unrelated property changes.** Budget for it when you adopt copy-on-evaluation.

### For UI: subscribe to addresses, not to categories

A message bus where regions subscribe to the *address of the specific property* they display, and a
write to that property notifies exactly those regions. Compare with notifier categories
("something in the scene changed"), which redraw everything and get coarser over time as people add
cases. The address-based version cannot rot the same way.

---

## 3. Operator discipline (nested operations on shared mutable state)

From BMesh, which has ~100 operations that call each other on one shared mesh:

- **Named, typed slots for input and output** (int / float / vec / mat / pointer / element buffer /
  map) rather than positional arguments. Operations chain by feeding one's output buffer to
  another's input.
- **Per-invocation tool flags.** Each operator call allocates its *own* set of per-element mark
  bits. A nested operator physically cannot clobber its caller's marks. This is what makes
  arbitrary nesting safe.
- **A hard rule: operators never read persistent state flags** (selection, hidden). They act only on
  their input slots. An operation that reads the selection is not composable, because a caller
  cannot invoke it on a subset.
- **Naming tiers that encode layering**: `bmesh_kernel_*` (primitive euler operators) /
  `BM_*` (public API) / `BMO_*` (operator API) / `bmo_*` (operator internals) / `bm_*` (file-static).
  You can tell from a call site which layer you are in.

The transferable idea is the second and third: **give each invocation private scratch marks, and
forbid operations from reading ambient state.** Those two rules together are what make composition
work; slots are just ergonomics.

---

## 4. Kernel fusion in a dataflow graph

When a graph of per-element operations is evaluated node-by-node, every edge is a full intermediate
buffer. For image or field data that is almost all of the cost.

The fix is to **group adjacent pixel-wise/element-wise nodes into a compile unit and generate one
kernel for the whole group**:

- On GPU: emit a single shader for the group, with textures bound only at the group's boundary.
- On CPU: compile the group into a single procedure evaluated once per element.

Blender's compositor does exactly this, and geometry nodes does the analogous thing for fields:
a composed field expression DAG is compiled into a **multi-function procedure** — a small IR with
variables and Call / Branch / Destruct / Return instructions, a builder, and optimization passes —
then executed over the whole array once.

Two supporting decisions that make fusion practical:

- **Schedule with an objective.** The traversal order is chosen by a heuristic on peak live buffer
  count, not just topological order. Order matters enormously for memory when buffers are large.
- **Defer resampling.** Give each value a "domain" (resolution + transform + interpolation and
  extension policy) and make realizing one domain onto another an explicit, optimizable step,
  rather than eagerly resampling at every edge.

If you are building any evaluation graph over bulk data, fusion is where the order-of-magnitude is.
Node-at-a-time evaluation is a prototype, not a design.

---

## 5. Laziness that composes through nesting

A demand-driven function that can be re-entered:

- It is called; it sees which outputs are wanted; it requests only the inputs it needs; it returns.
- The caller computes those inputs and calls it again; it advances.
- Repeat until the required outputs are ready.

Effectively a state machine with a calling convention. Values carry a usage state — `Used`,
`Maybe`, `Unused` — so a callee can distinguish "definitely needed" from "compute if cheap".

The property that makes it worth the complexity is **composition through nesting**: a switch node
inside a nested group can prevent evaluation of a node in the *parent* graph, because the laziness
propagates outward through the group's own lazy interface. A design where laziness stops at the
group boundary buys you very little.

Complementary analyses, all cheap and all worth having in any node system:

- **Usage inference** — which sockets/inputs can never affect the output (drives greying-out in the
  UI, and dead-code elimination in evaluation).
- **Abstract interpretation** — propagate *which parts* of a value are affected rather than values
  themselves. Blender's `ValueElem` types hold only booleans (a `VectorElem` is three bools, one
  per component). Cheap enough to run interactively.
- **Inverse evaluation** — given a desired output value, backpropagate to find inputs that produce
  it. This is what makes a viewport gizmo able to drag a procedurally-generated result and have the
  right upstream parameter change.
- **Partial evaluation** — a separate, non-recursive, low-startup evaluator for when only a few
  cheap nodes need running. Deliberately *not* the optimized one; different objective (latency, not
  throughput).

---

## 6. Plugin vtables — the parts people leave out

The basic pattern (a struct of function pointers per plugin type, registered in a table) is
well-known. The parts that separate a good one from a bad one:

- **`required_data_mask`** — each plugin *declares which data layers it needs*, so the pipeline can
  prune everything else before running the stack. Without this, every stage carries every layer.
- **`depends_on_time` / `depends_on_normals`** — declarative dependency queries, so the scheduler
  can answer questions about the stack without running it.
- **`update_depsgraph`** — the plugin registers its own edges into the dependency graph. The graph
  does not need to know the plugin's semantics.
- **`is_disabled`** with a reason — a plugin can declare itself inapplicable given current settings,
  and the UI can say why.
- **`foreach_ID_link`** — generic traversal of the plugin's references to other objects, so
  copy / delete / remap / dependency-collection are written once for all plugin types.
- **`blend_read` / `blend_write`** — per-plugin serialization hooks, so persistence is not a
  centralized switch statement that every new plugin must edit.

The through-line: **plugins should declare their requirements and relationships, not just their
behavior.** Every declaration removes a place where the host has to special-case them.
