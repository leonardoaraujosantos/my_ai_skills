# Setup, Tools, and `execute_blender_code` Gotchas

## Install & connection

The working server is the **official Blender Lab MCP** (from `projects.blender.org/lab/blender_mcp`), cloned at `~/blender_mcp`, registered as:

```
uv --directory /Users/<user>/blender_mcp/mcp run blender-mcp
```

Register in user scope:
```bash
claude mcp add blender -s user -- uv --directory ~/blender_mcp/mcp run blender-mcp
```

**Critical compatibility note:** the add-on inside Blender is the official "MCP" extension (`lab_blender_org/mcp`), listening on `localhost:9876` with a null-byte-delimited JSON protocol. It is NOT compatible with the popular third-party `uvx blender-mcp` (ahujasid) package — that pairing fails with `Incomplete JSON response received`. Add-on and server must both be the official Blender Lab project.

Blender side: Preferences → Add-ons → **MCP** → enable "Auto Start" (binds port 9876). Requires Blender 5.1+.

### Connection recovery
If a Blender tool call returns `Cannot connect to Blender at localhost:9876`, **Blender crashed** (the server process may linger as an orphan; the port closes). Steps:
1. Confirm: `pgrep -fl -i blender` (look for the actual `Blender.app` process, not just `blender-mcp` servers) and `lsof -iTCP:9876 -sTCP:LISTEN`.
2. Ask the user to reopen Blender with their scene (and re-enable MCP if Auto Start is off).
3. Reconnect this session with `/mcp`.
4. Nothing scripted is truly lost — the whole pipeline is reproducible from the conversation — but **unsaved `.blend` state is gone**. This is why you save early and often.

## The 26 tools, grouped

- **Inspection** — `get_objects_summary` (scene hierarchy, active object, mode, collections), `get_object_detail_summary` (transforms, modifiers, constraints, materials, vertex groups). Always inspect before mutating; the add-on's own rule is "never assume, inspect first."
- **Blend-file audit** — `get_blendfile_summary_*` (10 variants): datablocks, missing files, linked libraries, path info, usage guess.
- **Code execution** — `execute_blender_code` (+ `_for_cli`). The workhorse; see gotchas below.
- **Visual capture** — `render_viewport_to_path`, `render_thumbnail_to_path`, and the three `get_screenshot_of_*` (one is buggy — see below).
- **UI navigation** — `jump_to_tab_by_name`, `jump_to_tab_by_space_type`, `jump_to_view3d_object_by_name`, `jump_to_view3d_object_data_by_name`.
- **Documentation** — `search_api_docs`, `get_python_api_docs`, `search_manual_docs`. The server ships the full Python API reference and user manual as searchable RST. Consult them before writing `bpy` you're unsure of — cuts hallucination against the exact Blender version.

## The screenshot bug — use renders instead

`get_screenshot_of_area_as_image` (and the window variants) frequently fail with:
```
Invalid response from Blender at localhost:9876: Unterminated string starting at: line 1 column 61 (char 60)
```
It's a transfer bug in the add-on, not your fault. **Workarounds:**
- For normal shaded views: `render_viewport_to_path("name.png")`, then `Read` the returned filepath. (It returns a temp path like `/var/folders/.../blender_mcp/name.png`.)
- **For armature overlays** (bones, custom widgets, empties — these do NOT appear in a normal render): drive an OpenGL viewport render, which bakes the overlays:

```python
import bpy
scene = bpy.context.scene
out = "/tmp/rig_view.png"
old_fp, old_fmt = scene.render.filepath, scene.render.image_settings.file_format
scene.render.filepath = out
scene.render.image_settings.file_format = 'PNG'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.render.opengl(view_context=True, write_still=True)
            break
scene.render.filepath, scene.render.image_settings.file_format = old_fp, old_fmt
result = {"ok": True}
```

## `execute_blender_code` gotchas

This is the tool you use for ~everything. Prefer `bpy.ops` for standard actions (they handle context/defaults), `bpy.data` for precise control. Traps that actually bit:

1. **`result` must be a dict, not a list.** `result = [1,2,3]` → `The result variable must be a dict`. Wrap it: `result = {"items": [...]}`.
2. **Main-thread execution.** Code runs on Blender's main thread, so heavy ops (high-res voxel remesh, big geometry-node eval) **freeze the UI** for their duration. Fine, just expect it; warn the user before a long op if they're mid-interaction.
3. **Blender 5.x action-slot API.** The animation-data model changed. `action.fcurves` no longer exists — an Action holds `layers → strips → channelbags → fcurves`:
   ```python
   n = sum(len(cb.fcurves) for L in act.layers for s in L.strips for cb in s.channelbags)
   ```
   And after assigning an action you often must bind the **slot** or the object won't animate:
   ```python
   ad.action = bpy.data.actions["Walk"]
   if ad.action_slot is None and len(ad.action.slots):
       ad.action_slot = ad.action.slots[0]
   ```
   Symptom of a missing slot bind: object sits in rest pose despite an assigned action.
4. **FFMPEG/video export removed in Blender 5.2.** `render.image_settings.file_format = 'FFMPEG'` throws `enum "FFMPEG" not found`. Render a PNG sequence and mux with ffmpeg on the host:
   ```bash
   ffmpeg -y -framerate 24 -i frames/f_%04d.png -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart out.mp4
   # loop a cycle N times:  add  -stream_loop N  before -i
   ```
5. **`numpy` is available** inside Blender's Python — use it for geometry math (vertex arrays via `foreach_get`/`foreach_set`, distance fields, connectivity). Huge speedup over per-vertex Python loops.
6. **`bpy_struct` doesn't expose `Bone.select`** in this build — select via pose bones / edit bones or `bone.select` on edit bones only. Read pose state from the evaluated object.
7. **Evaluate the depsgraph before reading computed values** (world matrices, modifier/constraint results):
   ```python
   dg = bpy.context.evaluated_depsgraph_get()
   ev = obj.evaluated_get(dg)   # ev.pose.bones[...] reflects constraints/drivers
   ```
   After changing a driver-backed property, call `rig.update_tag(); bpy.context.view_layer.update()` before re-reading, or the value looks stale.

## Long renders: run the wait in the background

Renders block. Kick off `bpy.ops.render.render('INVOKE_DEFAULT', animation=True)` (non-blocking inside Blender), then poll for the last frame file on the host in a background Bash task so the turn isn't held:

```bash
D=frames; deadline=$((SECONDS+1200))
while [ $SECONDS -lt $deadline ]; do
  if [ -f "$D/f_0048.png" ]; then
    s1=$(stat -f%z "$D/f_0048.png"); sleep 3; s2=$(stat -f%z "$D/f_0048.png")
    [ "$s1" = "$s2" ] && [ "$s1" -gt 0 ] && { echo DONE; exit 0; }
  fi; sleep 10
done; echo TIMEOUT; exit 1
```
The stat-twice check ensures the last frame finished writing before muxing.
