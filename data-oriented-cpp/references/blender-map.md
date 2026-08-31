# Where to read the originals

Every pattern in this skill has a production implementation in the Blender source. Paths are
relative to a Blender checkout root and were verified against `main` (Blender 5.x, 2026-08).
Clone: `https://projects.blender.org/blender/blender`

Read the **headers first** — Blender's convention is that the design rationale lives in the header
doc-comment, and those comments are unusually good. Several are better than any blog post on the
same topic.

---

## Collections and representation

| Pattern | Path | Note |
|---|---|---|
| Compressed index set | `source/blender/blenlib/BLI_index_mask.hh` | Read the `max_segment_size` comment — the constant is justified in four bullet points |
| Index set algebra | `source/blender/blenlib/BLI_index_mask_expression.hh` | `ExprBuilder`, single-pass evaluation |
| Virtual arrays | `source/blender/blenlib/BLI_virtual_array.hh` | File header states the tradeoff honestly |
| Devirtualization | `source/blender/blenlib/BLI_devirtualize_parameters.hh` | Read the warning about exponential code growth |
| Devirtualization in use | `source/blender/nodes/function/nodes/node_fn_combine_matrix.cc` | Small, complete example |
| Implicit sharing / COW | `source/blender/blenlib/BLI_implicit_sharing.hh` | Strong/weak counts + version; helpers at the bottom |
| Sharing-aware lazy cache | `source/blender/blenlib/BLI_shared_cache.hh` | Cache shared between original and evaluated copy |
| CSR grouping | `source/blender/blenlib/BLI_offset_indices.hh` | Note the `NoSortCheck` debug-build escape hatch |
| Runtime type erasure | `source/blender/blenlib/BLI_cpp_type.hh`, `BLI_any.hh`, `BLI_generic_*.hh` | |
| Hierarchical context hashing | `source/blender/blenlib/BLI_compute_context.hh` | Excellent problem statement in the header |
| Runtime scope / optional ownership | `source/blender/blenlib/BLI_resource_scope.hh` | |
| Chunked dedup array store | `source/blender/blenlib/BLI_array_store.hh` | The chunk-size tradeoff is documented |
| Attribute layer | `source/blender/blenkernel/BKE_attribute.hh` | Domain adaptation, lookup-or-default |
| Anonymous attributes | `source/blender/blenkernel/BKE_anonymous_attribute_id.hh` | Plus `BKE_geometry_nodes_reference_set.hh` for the lifetime tracking |
| Typed geometry container | `source/blender/blenkernel/BKE_geometry_set.hh` | |

## Parallelism

| Pattern | Path | Note |
|---|---|---|
| Ownership partition | `source/blender/blenkernel/BKE_paint_bvh.hh` | `MeshNode::vert_indices_`, `unique_verts_num_`, `verts()` vs `all_verts()` — read this comment |
| Lazy threading | `source/blender/blenlib/BLI_lazy_threading.hh` | The best doc-comment in the library |
| Task API, bandwidth throttle, isolation | `source/blender/blenlib/BLI_task.hh` | `memory_bandwidth_bound_task`, `isolate_task`, `max_threads_task` |
| Task size hints | `source/blender/blenlib/BLI_task_size_hints.hh` | `AccumulatedLookup` pairs with CSR offsets |
| Lazy cache primitive | `source/blender/blenlib/BLI_cache_mutex.hh` | Lists the pitfalls it exists to prevent |
| Thread-local scratch | `source/blender/blenlib/BLI_enumerable_thread_specific.hh` | |
| Scratch + partition in anger | `source/blender/editors/sculpt_paint/mesh/brushes/draw.cc` | ~200 lines, three backends, the whole pattern end to end |

## Architecture

| Pattern | Path | Note |
|---|---|---|
| Normalize-then-operate | `source/blender/editors/transform/` | `transform.hh` for `TransData`; `transform_convert_*.cc` (28 converters); `transform_mode_*.cc` (~30 operations) |
| Converter contract | `source/blender/editors/transform/transform_convert.hh` | |
| Dependency graph tiers | `source/blender/depsgraph/intern/node/` | ID / component / operation nodes |
| Tag and flush | `source/blender/depsgraph/intern/depsgraph_tag.cc`, `intern/eval/deg_eval_flush.cc` | |
| Runtime backup across COW | `source/blender/depsgraph/intern/eval/deg_eval_runtime_backup_*.cc` | Ten files. The unglamorous part |
| Message bus | `source/blender/windowmanager/message_bus/wm_message_bus.hh` | Subscribe to RNA property addresses |
| Operator discipline | `source/blender/bmesh/bmesh.hh` | Read the whole file header: slots, per-invocation tool flags, the no-header-flags rule, naming tiers |
| Plugin vtable | `source/blender/blenkernel/BKE_modifier.hh` | `ModifierTypeInfo` — note `required_data_mask`, `depends_on_time`, `update_depsgraph`, `is_disabled` |
| Kernel fusion (GPU) | `source/blender/compositor/COM_shader_operation.hh` | |
| Scheduling for peak memory | `source/blender/compositor/COM_scheduler.hh` | |
| Deferred resampling | `source/blender/compositor/COM_domain.hh` | |
| Retained-mode draw commands | `source/blender/draw/intern/draw_pass.hh` | `PassMain` vs `PassSimple` vs `PassSortable`, tradeoffs stated |

## Evaluation graphs and compilers

| Pattern | Path | Note |
|---|---|---|
| Throughput calling convention | `source/blender/functions/FN_multi_function.hh` | |
| Expression DAG | `source/blender/functions/FN_field.hh` | Compiles to a procedure |
| The IR | `source/blender/functions/FN_multi_function_procedure.hh` | Variables + Call/Branch/Destruct/Return; builder and optimization passes alongside |
| Composable laziness | `source/blender/functions/FN_lazy_function.hh` | The switch-node walkthrough is the clearest explanation of the idea anywhere |
| Liveness / usage inference | `source/blender/nodes/NOD_socket_usage_inference.hh` | |
| Abstract interpretation | `source/blender/nodes/NOD_value_elem.hh` | `VectorElem` is three bools |
| Inverse evaluation | `source/blender/nodes/NOD_inverse_eval_run.hh` | Backpropagate a desired output to inputs |
| Partial evaluation | `source/blender/nodes/NOD_partial_eval.hh` | Deliberately unoptimized, low startup, non-recursive |
| Closures in a visual language | `source/blender/nodes/NOD_geometry_nodes_closure.hh` | |
| A full shader compiler front-end | `source/blender/gpu/shader_tool/` | Lexer, Pratt parser (`pratt_parser.hh`), AST, symbol tables, templates, codegen |

## Persistence

| Pattern | Path | Note |
|---|---|---|
| Self-describing schema | `source/blender/makesdna/DNA_genfile.h` | `DNA_reconstruct_info_create`, `DNA_struct_reconstruct`, `eSDNA_StructCompare` |
| Schema generator | `source/blender/makesdna/intern/makesdna.cc` | Build-time parser; the single source of truth |
| Versioning discipline | `source/blender/blenloader/intern/versioning_*.cc` | One file per release, append-only. `versioning_common.cc` for helpers, `versioning_xxx_template.cc` for the shape of a new one |
| Chunked dedup undo | `source/blender/blenloader/BLO_undofile.hh` | `MemFileChunk`, `is_identical`, `is_identical_future`, sharing passthrough |
| Per-region typed undo | `source/blender/editors/sculpt_paint/mesh/sculpt_undo.hh` | Concurrent push, typed restore, byte-plane prefilter + zstd |

---

## Suggested reading order

If you are studying rather than looking something up:

1. `BLI_offset_indices.hh` — shortest, and the count-scan-fill idiom shows up everywhere else.
2. `BLI_index_mask.hh` — read only the header comment and the `foreach_*` methods.
3. `BKE_paint_bvh.hh` `MeshNode` — ownership partition, ~40 lines of comment.
4. `sculpt_paint/mesh/brushes/draw.cc` — sees 1-3 used together in real code.
5. `BLI_lazy_threading.hh` — pure prose, no API to learn, changes how you think about grain size.
6. `BLI_implicit_sharing.hh` — then `BLI_shared_cache.hh` immediately after.
7. `editors/transform/transform.hh` + any two `transform_convert_*.cc` — the architecture payoff.
8. `DNA_genfile.h` + one `versioning_*.cc` — how a format survives twenty years.
9. `FN_lazy_function.hh` — if you build evaluation graphs.

Steps 1-4 are about half a day and cover most of the practical value.
