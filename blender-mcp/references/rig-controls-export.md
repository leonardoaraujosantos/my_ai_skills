# IK Controls, Production Widgets, and FBX Export

## IK as a non-destructive control layer

The key principle: **IK is a control layer on top of the deform bones, not a change to them.** Done right it does not alter the existing (FK-baked) animations and does not change the exported skeleton. Verify both claims (below) — don't assume.

### Build
Add non-deforming control bones (foot targets + pole targets), parented to `root`:
```python
b = eb.new(f"CTRL_foot.{q}"); b.head = foot; b.tail = foot + Vector((d.x*0.45, d.y*0.45, 0))
b.parent = eb["root"]; b.use_deform = False
p = eb.new(f"CTRL_pole.{q}"); p.head = pole; p.tail = pole + Vector((0,0,0.35))
p.parent = eb["root"]; p.use_deform = False
```
Add an IK constraint on the last deform bone of each chain, targeting the foot control, poled by the pole control, `chain_count = <segments>`, `use_tail = True`, `influence = 0.0` initially.

### FK/IK blend via one property + drivers
A custom property on `root` drives every IK constraint's influence, so one slider flips the whole rig:
```python
root["ik_blend"] = 0.0     # 0 = FK (existing anims), 1 = IK
fcurve = ik.driver_add("influence"); drv = fcurve.driver; drv.type = 'AVERAGE'
var = drv.variables.new(); var.name = "blend"; var.type = 'SINGLE_PROP'
var.targets[0].id = rig
var.targets[0].data_path = 'pose.bones["root"]["ik_blend"]'
```
Keep `ik_blend = 0` by default so FK animations pass through untouched.

### Pole-angle calibration (the tricky part)
A 3-segment zig-zag leg inverts its knee under a wrong pole angle. Calibrate numerically: with a **test foot offset applied** (not the rest pose — at rest the IK has nothing to solve and every angle scores 0), sweep `pole_angle` over 360° and pick the angle that satisfies **both** criteria — keep the knee above the elbow (zig-zag preserved) AND keep the leg in its radial plane. Between candidate angles, reset the pose (`ik_blend=0` then `1`, `update_tag`, `view_layer.update()`) so each solve is deterministic.

### Verify it didn't break anything
1. **Animations identical:** sample every bone's pose matrix at several frames of each clip, before and after adding IK; assert max difference `< 1e-4`. (Stash a baseline dict in a scene property before building the rig.)
2. **Exported skeleton unchanged:** export with `use_armature_deform_only=True` (control bones are `use_deform=False`, so they're excluded), then confirm on the host that the control names are absent from the FBX:
   ```bash
   strings quadbot.fbx | grep -c CTRL_foot   # expect 0
   strings quadbot.fbx | grep -c QuadWalk     # expect >0 (clip present)
   ```

## Production control widgets (custom shapes, colors, collections)

Bones as octahedra are hard to click; give controls real widget shapes and side-colors. This is **viewport-only** — it never affects deformation or the export, so no re-export needed.

1. **Widget meshes** in a hidden `WGT` collection (circle, diamond, cube, ring). Build with `mesh.from_pydata(verts, edges, [])`; set `hide_render=True`.
2. **Assign per pose bone:**
   ```python
   p = pb["CTRL_foot.FL"]; p.custom_shape = bpy.data.objects["WGT_circle"]
   p.use_custom_shape_bone_size = False
   p.custom_shape_scale_xyz = (0.38, 0.38, 0.38)
   ```
3. **Colors** via theme palettes (convention: red=left, blue=right):
   ```python
   rig.data.bones["CTRL_foot.FL"].color.palette = 'THEME01'  # red
   rig.data.bones["CTRL_foot.FR"].color.palette = 'THEME04'  # blue
   # THEME03 green (poles), THEME06 purple (body), THEME09 yellow (root)
   ```
   Avoid THEME01 (red) on the body — it reads as "left". Use a distinct hue.
4. **Bone collections** to hide deform bones so only controls are clickable:
   ```python
   col_ctrl = rig.data.collections.new("Controles")
   col_def  = rig.data.collections.new("Deform")
   for b in rig.data.bones:
       if b.name.startswith("CTRL_") or b.name in ("root","body"): col_ctrl.assign(b)
       if b.use_deform and b.name != "root": col_def.assign(b)
   col_def.is_visible = False
   rig.data.show_bone_custom_shapes = True; rig.show_in_front = True
   ```
5. To see the result, use the **OpenGL viewport render** (bones/widgets don't appear in a normal render) — see `references/setup.md`.

Reorient a foot control's `tail` straight up so a circle widget lies flat on the ground; this doesn't affect IK (the constraint uses target position, not rotation).

## FBX export for Unity / Unreal

The settings that produce clean game imports (all verified against this project):
```python
bpy.ops.export_scene.fbx(
    filepath="/path/quadbot.fbx",
    use_selection=True, object_types={'ARMATURE', 'MESH'},
    apply_scale_options='FBX_SCALE_ALL',       # avoids the classic 0.01 scale on import
    add_leaf_bones=False,                       # no phantom _end bones in Unity
    use_armature_deform_only=True,              # exclude CTRL_* control bones
    bake_anim=True, bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=True,              # each NLA strip → a separate clip
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0, bake_anim_simplify_factor=0.0,   # per-frame, no lossy simplify
    path_mode='COPY', embed_textures=True,
)
```
Notes:
- **Apply transforms** on the mesh before export (rotation/scale) or it imports skewed.
- **Root at ground origin**; in-place cycles (move the character in-engine via code/NavMesh — the game-AI standard). Match move speed to the cycle's stride so feet don't slide (stride ≈ yaw amplitude × leg length; e.g. ~0.45 u/s for a 2s cycle).
- **Unity:** Generic rig (not Humanoid) for a non-biped; mark Walk/Idle clips as looping.
- **Unreal:** imports as Skeletal Mesh + N Animation Sequences → State Machine (Idle↔Walk blend, Die terminal).
- Set `bake_anim_use_nla_strips=True` and **unmute all NLA tracks** before exporting, so every clip is written. Re-mute afterward for viewport sanity.
- Re-export is only needed after mesh/skeleton/animation changes — never for widget/color/collection edits.
