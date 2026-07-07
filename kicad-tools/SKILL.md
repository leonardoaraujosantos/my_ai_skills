---
name: kicad-tools
description: Drive KiCad from the command line via kicad-cli - run ERC/DRC design checks with parsed JSON reports, export schematics (PDF/SVG/netlist/BOM), generate PCB fab outputs (gerbers, drill, pick-and-place), and render boards. Use when the user says "export gerbers/BOM from KiCad", "run ERC/DRC", "check my KiCad project", "generate fab files", or "render the board/schematic to PDF".
argument-hint: <project.kicad_pro|board.kicad_pcb|sch.kicad_sch> [action]
---

# KiCad Tools

Drive KiCad headlessly through `kicad-cli`. All commands operate on `.kicad_sch` / `.kicad_pcb` files directly — no GUI needed.

## 1. Setup

Locate the binary (PATH first, then the macOS app bundle):

```bash
KICAD_CLI="$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)"
"$KICAD_CLI" version
```

If neither exists, install with:

```bash
brew install --cask kicad
```

Suggest the user add an alias so `kicad-cli` works in every shell:

```bash
alias kicad-cli="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
```

**Version caveat (important):** subcommands and flags differ between KiCad 7, 8, and 9. This document targets KiCad 8/9 syntax. Before running any unfamiliar export, confirm the exact flags at runtime:

```bash
"$KICAD_CLI" sch --help
"$KICAD_CLI" pcb --help
"$KICAD_CLI" pcb export --help
"$KICAD_CLI" pcb export gerbers --help   # etc. per subcommand
```

## 2. Design checks (ERC / DRC)

The centerpiece of this skill. Always export as JSON and parse it — never make the user read raw output.

```bash
mkdir -p out
"$KICAD_CLI" sch erc  project.kicad_sch --format json -o out/erc.json --exit-code-violations
"$KICAD_CLI" pcb drc  board.kicad_pcb  --format json -o out/drc.json --exit-code-violations
```

- `--exit-code-violations` makes the command return exit code 5 when violations exist, so CI can gate on it.
- DRC extras worth offering: `--schematic-parity` (checks board against schematic) and `--severity-error` / `--severity-warning` / `--severity-all` to filter what is reported.

After running, **parse the JSON** (`violations` array; each entry has `type`, `severity`, `description`, and `items` with reference designators and `pos` coordinates in the `coordinate_units` of the report). Then:

1. Group violations by severity (error > warning) and by `type`.
2. Explain each violation type in plain language (e.g. `unconnected_items` = a pin/pad has no net connection).
3. Point at the offending refs and coordinates so the user can find them in the editor (e.g. "R5 pad 2 at (132.5, 88.2) mm").
4. Summarize: N errors, M warnings, and whether the design is clean enough to proceed to fab outputs.

## 3. Schematic exports

```bash
# PDF (whole schematic, all sheets)
"$KICAD_CLI" sch export pdf project.kicad_sch -o out/schematic.pdf

# SVG (one file per sheet, into a directory)
"$KICAD_CLI" sch export svg project.kicad_sch -o out/svg/

# Netlist (default KiCad s-expression)
"$KICAD_CLI" sch export netlist project.kicad_sch -o out/project.net

# SPICE netlist — feeds the spice skill for simulation
"$KICAD_CLI" sch export netlist project.kicad_sch --format spice -o out/project.cir

# BOM (CSV) with chosen fields, grouped by value+footprint
"$KICAD_CLI" sch export bom project.kicad_sch -o out/bom.csv \
  --fields "Reference,Value,Footprint,${QUANTITY},MPN" \
  --group-by "Value,Footprint"
```

Notes:
- `--fields` takes symbol field names plus generated columns like `${QUANTITY}` and `${DNP}`; `--labels` renames the CSV headers; `--exclude-dnp` drops do-not-populate parts. Check `sch export bom --help` — BOM flags changed the most between versions.
- Netlist `--format` also supports `kicadxml`, `cadstar`, `orcadpcb2`, `spicemodel` on recent versions.

## 4. PCB fab outputs

```bash
mkdir -p out/fab

# Gerbers — select layers explicitly (adjust Cu layers to the stackup)
"$KICAD_CLI" pcb export gerbers board.kicad_pcb -o out/fab/ \
  --layers "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts"

# Drill files — Excellon, one common convention set
"$KICAD_CLI" pcb export drill board.kicad_pcb -o out/fab/ \
  --format excellon --excellon-units mm --generate-map --map-format gerberx2

# Pick-and-place (component positions)
"$KICAD_CLI" pcb export pos board.kicad_pcb -o out/fab/board.pos \
  --format csv --units mm --side both

# 3D / assembly-data exports (where the installed version supports them)
"$KICAD_CLI" pcb export step board.kicad_pcb -o out/board.step
"$KICAD_CLI" pcb export vrml board.kicad_pcb -o out/board.wrl
"$KICAD_CLI" pcb export ipc2581 board.kicad_pcb -o out/board.xml   # KiCad 8+
```

### Standard fab package recipe

Produce a zip a board house accepts:

```bash
mkdir -p out/fab
"$KICAD_CLI" pcb export gerbers board.kicad_pcb -o out/fab/ \
  --layers "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts"
"$KICAD_CLI" pcb export drill board.kicad_pcb -o out/fab/ \
  --format excellon --excellon-units mm --generate-map
cd out && zip -r fab_package.zip fab/ && cd -
```

**Fab package checklist — verify before handing over:**
- [ ] All copper layers for the stackup included (In1.Cu, In2.Cu, ... for 4+ layer boards)
- [ ] Edge.Cuts (board outline) present
- [ ] Mask and silk for both sides
- [ ] Paste layers included only if the fab also does the stencil
- [ ] Drill file units (mm vs inch) match the fab's requirements; map file included
- [ ] PTH and NPTH drills present (merged or separate per fab preference — see `--excellon-separate-th`)
- [ ] Origin convention consistent (use `--use-drill-file-origin` on gerbers/pos if the fab expects the drill/place origin instead of the page origin)
- [ ] DRC was clean (Section 2) before generating any of this

## 5. Board renders

```bash
# Per-layer documentation PDF / SVG
"$KICAD_CLI" pcb export pdf board.kicad_pcb -o out/board.pdf --layers "F.Cu,F.SilkS,Edge.Cuts"
"$KICAD_CLI" pcb export svg board.kicad_pcb -o out/board.svg --layers "F.Cu,Edge.Cuts" --page-size-mode 2

# Raytraced 3D render (KiCad 8+ — confirm with `pcb render --help`)
"$KICAD_CLI" pcb render board.kicad_pcb -o out/board-top.png --side top --quality high
"$KICAD_CLI" pcb render board.kicad_pcb -o out/board-bottom.png --side bottom
```

If `pcb render` is missing (KiCad 7), fall back to per-layer SVG exports.

## 6. Common workflows

### Pre-review checklist

1. **ERC** on the schematic (Section 2) — resolve or explain every error.
2. **DRC** on the board with `--schematic-parity` — catches board/schematic drift.
3. **BOM sanity**: export the BOM and scan for empty `Value` fields, missing/unmatched `Footprint` fields, and duplicate reference designators. Report anything suspicious before fab outputs.

### Diffing two revisions

Export SVGs of the same layers from both revisions into separate directories and compare:

```bash
"$KICAD_CLI" pcb export svg rev_a/board.kicad_pcb -o out/rev_a.svg --layers "F.Cu,Edge.Cuts"
"$KICAD_CLI" pcb export svg rev_b/board.kicad_pcb -o out/rev_b.svg --layers "F.Cu,Edge.Cuts"
```

Then diff visually (overlay, or rasterize and use ImageMagick `compare`). Repeat per layer of interest. The same works for schematics via `sch export svg`.

### Python scripting escape hatch

For anything kicad-cli cannot do (custom board queries, bulk footprint edits, programmatic geometry), KiCad ships the `pcbnew` Python API. Run scripts with KiCad's bundled interpreter so the module resolves: `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` on macOS (or `kicad-cli`'s sibling python on other platforms), then `import pcbnew; board = pcbnew.LoadBoard("board.kicad_pcb")`. Prefer kicad-cli whenever it covers the task.

## 7. Rules

- **Never modify project files.** All operations here are read-only exports; do not edit `.kicad_pro`, `.kicad_sch`, or `.kicad_pcb`.
- **All exports go to `out/`** (or a user-specified directory) — never scatter generated files next to the sources.
- **Confirm flags before unfamiliar exports.** Flags vary between KiCad 7/8/9; run `kicad-cli <group> <command> --help` first and adapt.

## Pairs with

- **spice** — simulate the netlist from `sch export netlist --format spice`.
- **datasheet** — verify footprints and pinouts against part cards before fab.
