# Persistence, versioning, and undo

Reference implementations: `source/blender/makesdna/`, `source/blender/blenloader/`,
`source/blender/blenlib/BLI_array_store.hh`.

---

## 1. Self-describing binary format (SDNA)

### The problem with the obvious design

A binary reader that does `fread(&my_struct, sizeof(MyStruct), 1, f)` is correct exactly once. Add a
field, reorder members, change an `int` to a `float`, and every previously written file is garbage.
The usual mitigations — a format version integer plus a migration function per version — mean
writing migration code for *every* schema change, including the 95% that are trivial field additions.

### The design

**Write a machine-readable description of every struct into the file itself.** Blender's SDNA block
contains, for each struct the writer knew about: its name, its field names, and its field types.
It is generated at build time by a tool that parses the header files, so it cannot drift from the
code.

On load:

1. Read the file's SDNA and compare it against the running build's SDNA.
2. Classify each struct: `EQUAL` (byte-copy), `NOT_EQUAL` (field-by-field), `REMOVED` (skip).
3. For `NOT_EQUAL` structs, **match old fields to new fields by name and type** and copy what
   matches. New fields keep their defaults. Removed fields are dropped. Reordered fields just work.
4. Precompute this mapping *once* per struct pair (`DNA_reconstruct_info_create`) so the per-instance
   path is a table walk, not a string comparison.

The result: adding, removing, or reordering a field requires **zero** migration code. This is why
Blender opens files from 2003.

### What still needs explicit migration

Anything **semantic**:

- units changed (degrees to radians)
- one field split into two, or two merged
- a default flipped, where old files must keep the old behavior
- an enum value's meaning changed
- data moved to a different struct

Blender keeps one file per release — `versioning_250.cc` ... `versioning_503.cc` — each with a
`if (file_version < X) { ... }` block. Rules that make this sustainable:

- **Append-only.** Never edit an old versioning function; files already migrated through it will not
  run it again.
- **One file per release**, never a single growing file.
- **Guard on the file's version, not on a feature flag.**
- Read `versioning_common.cc` for shared helpers before writing a new one by hand.

### Adopting this

You do not need a build-time C parser. The reusable core is:

1. Emit a schema description (field names + types + offsets) alongside the data. Generate it from a
   single source of truth so it cannot drift.
2. On load, match by **name and type**, not by position or offset.
3. Precompute the old→new field mapping per struct pair, then apply it per instance.
4. Reserve hand-written migrations for semantic changes only, in append-only per-version units.

Steps 2 and 3 are the whole trick, and both are a few hundred lines.

---

## 2. Undo for large documents

### The two shapes

**Global undo (whole-document).** Serialize the document, but store it as **content-defined chunks
with deduplication**. Blender's `BLI_array_store` splits data into chunks and shares identical
chunks between undo steps, so consecutive steps that differ in one object cost only that object.

```c
BArrayStore *bs = BLI_array_store_create(stride, chunk_count);
```

The two parameters are a direct tradeoff, and the header states it plainly:

- **small `chunk_count`** → better dedup, more chunks to search and more `memcpy` calls to rebuild
- **large `chunk_count`** → less bookkeeping, but a small isolated edit duplicates more data

Additional layers on top in `BLO_undofile.hh` worth copying:

- Each chunk records the **session-unique ID of the datablock being written**, so the next step can
  find corresponding chunks to compare against — dedup is guided, not a blind global search.
- `is_identical` (matches the previous step) and `is_identical_future` (matches the next step) let
  the undo system detect an ID that did not change *at all* and skip it entirely.
- Implicit-sharing passthrough: shared buffers that did not change are referenced, never serialized.

**Local undo (per-region snapshots).** For an interactive tool touching a small part of a large
document, do not snapshot the document. Snapshot **only the chunks the operation touched**, typed by
what changed:

```cpp
enum class Type : int8_t { Position, HideVert, HideFace, Mask, Geometry, FaceSet, Color, ... };
undo::push_node(object, node, Type::Position);   // thread-safe for distinct nodes
```

Two properties that make this work:

- **Push is callable concurrently** as long as threads pass different nodes. The kernel that is
  already iterating chunks in parallel records undo data inline, with no extra pass.
- **The type tells the restore path what to restore.** A position-only edit does not save or restore
  visibility, masks, or colors.

### Compress the snapshots, with a prefilter

Raw float arrays compress badly with a general-purpose compressor because the entropy is spread
across every byte. **Prefilter by byte plane** — transpose so all the first bytes of each float are
adjacent, then all the second bytes, and so on — and *then* compress. Exponent bytes in a position
array are nearly constant, so the transposed stream is highly compressible.

```cpp
compression::filter_compress<T>(src, filter_buffer, compress_buffer);
compression::filter_decompress<T>(src, buffer, dst);
```

This is the same idea as a shuffle filter in HDF5/Blosc. It typically buys a large ratio improvement
*and* speed on float data, and costs about thirty lines.

---

## 3. Which to use

| Situation | Approach |
|---|---|
| Document-level operations, arbitrary scope | Global: serialize + chunked dedup |
| Interactive tool touching a bounded region | Local: per-chunk typed snapshots |
| Both (an editor with modes) | Both, with a rule for which operations use which |
| Snapshot cost is dominated by unchanged data | Add identity tracking (`is_identical`) and sharing passthrough |
| Snapshot memory dominated by float arrays | Byte-plane prefilter + zstd |

The decision is about **the scope of a typical operation**, not the size of the document. An editor
where most operations touch a small, known region should use local undo even if the document is
small; one where operations touch arbitrary things should use global undo even if the document is
huge.
