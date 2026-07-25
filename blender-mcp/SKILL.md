---
name: blender-mcp
description: Drive Blender through the official Blender Lab MCP server to model, sculpt (procedurally), build materials/shader-node trees, UV unwrap, rig, skin, animate, add IK controls, and export game-ready FBX to Unity/Unreal. Encodes the hard-won gotchas — the screenshot bug, Blender 5.x action-slot API, FFMPEG removal, main-thread freezes — and a visual verification methodology (render → read → fix) that catches errors code-reading hides. Use when the user says "in Blender", "model/sculpt/rig/animate this", "make a walk/idle/death cycle", "weight paint via MCP", "add IK", "export FBX for Unity/Unreal", or points at a running Blender scene.
argument-hint: [model|material|rig|animate|ik|export] [what]
---

# Blender via MCP

Operate a live Blender session through the **official Blender Lab MCP** server. Everything the Blender Python API (`bpy`) can do is reachable — modeling, geometry nodes, materials, UV, rigging, skinning, animation, physics, render, export. The one thing that is NOT reachable is **continuous brush gesture** (sculpt strokes, manual weight-paint dragging, freehand UV-island dragging). The division is by *interaction type*, not by Blender area: sculpt is not excluded, only the brush stroke is — remesh, smooth, multires, and procedural deformation all work by code.

## The one rule that matters most: verify visually, every step

The single biggest failure mode is trusting that generated `bpy` code did what you intended. It compiles, runs, returns `ok`, and looks fine in a textured render — while bones point the wrong way or weights leak. **After any change with a visual result, render it and actually look at the image.** This loop caught every real error across the work that produced this skill:

```
execute_blender_code  →  render_viewport_to_path  →  Read the PNG  →  fix  →  repeat
```

Do not skip the Read. A static textured render hides bone misalignment; use debug overlays (x-ray mesh + emissive bone cylinders, color-baked weights, orthographic views) — see `references/rigging.md`.

## Setup & the tools

The server is `uv --directory ~/blender_mcp/mcp run blender-mcp` (the **official** Blender Lab project, NOT the third-party `uvx blender-mcp`). Blender must be open with the "MCP" add-on running on port 9876. Full install, the 26 tools grouped, connection recovery, and the `execute_blender_code` gotchas are in **`references/setup.md`** — read it first if the connection is flaky or a tool errors oddly.

Task → reference map:

| Task | Reference |
|------|-----------|
| Install, connection recovery, the 26 tools, `execute_blender_code` gotchas, Blender 5.x API traps, the screenshot bug | `references/setup.md` |
| Blockout → remesh → procedural "sculpt", shader-node materials, texture baking, UV | `references/modeling.md` |
| Armatures, the visual joint-verification method, rigid mech skinning, weight color-debug | `references/rigging.md` |
| Procedural walk/idle/death cycles, the world→bone rotation math, NLA strips | `references/animation.md` |
| IK setup, FK/IK blend, pole calibration, custom control shapes/colors/collections, FBX export for Unity/Unreal | `references/rig-controls-export.md` |

## Non-negotiables (learned the hard way)

1. **Save the `.blend` as soon as anything is right** — `bpy.ops.wm.save_mainfile()`. Blender crashed repeatedly during this work; unsaved rigs were lost. The MCP connection dropping = Blender crashed; reconnect with `/mcp`.
2. **`render_viewport_to_path`, not `get_screenshot_*`** — the add-on's screenshot tool fails with `Unterminated string ... char 60`. For armature overlays (bones/widgets don't appear in normal renders) use an OpenGL viewport render (`references/setup.md`).
3. **`result` must be a dict**, never a list — `execute_blender_code` rejects lists.
4. **Apply transforms before rigging/exporting** — a mesh with rotation/scale bakes wrong into the engine.
5. **Ask for a reference sketch early** on anything ambiguous (joint placement, panel ownership). One user sketch resolved in minutes what geometry-guessing burned three deliveries on.
6. **Don't infer from vertex statistics alone.** "Highest vertex in the leg column" was a cannon, not a knee. Fit to the real geometry and confirm with an orthographic x-ray overlay before skinning.

## Typical flow for "rig and animate this model for a game"

1. Inspect (`get_objects_summary`, `get_object_detail_summary`); apply transforms.
2. Plan joints from geometry; **verify with x-ray + emissive-cylinder overlay in ORTHO**; ask for a sketch if unsure.
3. Build armature; **rigid** skin for mech (connectivity BFS from seed segments); **color-debug** the weights and render.
4. Procedural cycles (sine-based, loopable); verify extreme frames.
5. Pack cycles as NLA strips → one FBX with multiple clips.
6. Optional IK control layer (does not alter the deform result or the exported skeleton).
7. Export FBX (`use_armature_deform_only`, `bake_anim_use_nla_strips`, `FBX_SCALE_ALL`, `add_leaf_bones=False`, embed textures). Save `.blend`.
