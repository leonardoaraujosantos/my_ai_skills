# Rigging & Skinning — with the Visual Verification Method

Rigging is where "the code ran fine" lies to you most. This file encodes a methodology that took 4 failed deliveries to arrive at. **Follow the verification steps; do not skip to skinning.**

## Step 0: prep

Apply transforms first (`bpy.ops.object.transform_apply(rotation=True, scale=True)`) — a mesh at rotation 90°/scale 2 bakes wrong into the engine and throws off joint math. Inspect for a saved filepath; save early.

## Step 1: plan joints — but VERIFY before trusting them

Inferring joints from vertex statistics alone **fails on complex meshes.** Real failures from this project:
- "Highest vertices in the leg column" were a **cannon and hoses on top**, not knees. The femurs pointed at the sky.
- Legs looked like 2 segments but were a **3-segment zig-zag** (body → low elbow → high knee-hub → foot). The low-elbow geometry (z≈0.7) was mistakenly discarded as "underside of the shell."

**Ask the user for a reference sketch of one limb early.** One sketch resolved in minutes what geometry-guessing burned three deliveries on.

Then **verify placement with an overlay before building the real rig:**
1. Give the mesh a translucent x-ray material (`alpha ~0.22`, `blend_method='BLEND'`).
2. Add an emissive cylinder along each proposed bone.
3. Render in an **orthographic** camera (front and side). Ortho makes px↔world linear, so you can measure joint positions directly off the render and compare to the mesh silhouette.

```python
def add_bone_viz(a, b, mat):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=(b-a).length, location=(a+b)/2)
    c = bpy.context.active_object; c.name = "BoneViz"
    c.rotation_mode = 'QUATERNION'
    c.rotation_quaternion = (b-a).to_track_quat('Z', 'Y')
    c.data.materials.append(mat)
# ortho cam looking down -Y:
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6.5
cam.location = (0, -12, 1.6); cam.rotation_euler = (pi/2, 0, 0)
```

To refine a joint numerically, grid-search a 2-segment (or 3-segment) polyline that minimizes mean distance to the leg's real vertices (project onto the leg azimuth, fit `(hip_s, hip_z, knee_s, knee_z)`). Cross-check the fit against the vertex profile (bin by radial distance, look at median z and width — "waists" separate mechanical parts).

## Step 2: build the armature

```python
bpy.ops.object.armature_add(location=(0,0,0)); rig = bpy.context.active_object
rig.name = "QuadRig"; rig.data.name = "QuadRig"
bpy.ops.object.mode_set(mode='EDIT'); eb = rig.data.edit_bones
for b in list(eb): eb.remove(b)
def bone(name, head, tail, parent=None):
    b = eb.new(name); b.head, b.tail = head, tail
    if parent: b.parent = eb[parent]
# root at ground origin (Unity/Unreal convention) → body → per-leg chain
bone("root", (0,0,0), (0,0,0.5)); bone("body", (0,0,1.6), (0,0,2.8), "root")
# 3-bone leg: coxa (body→low elbow), femur (elbow→high knee), shin (knee→foot)
bpy.ops.object.mode_set(mode='OBJECT')
```
Name symmetric parts with a **consistent suffix**. Note: Blender's X-Mirror expects `.L`/`.R`; custom suffixes like `.FL/.FR/.RL/.RR` won't auto-mirror — each limb is posed individually.

## Step 3: skin — RIGID for mechanical models

Automatic weights (`parent_set(type='ARMATURE_AUTO')`) work for a clean organic mesh, but for **mech** you want rigid weights (each vertex 100% to one bone) so panels stay stiff. Compute assignment by connectivity, not raw nearest-segment:

1. **Seed** each part from vertices clearly within it (`d < 0.20` to the segment), and seed `body` from the shell (radial distance to center, cannon region, etc.). **Shrink the seed segment away from the body shell** (start at 30–45% along the bone) or it claims shell panels.
2. **Grow by BFS over the mesh edge graph** from the seeds — this respects topology (a hose that passes near a leg but isn't connected won't be captured).
3. Within a leg, split into coxa/femur/shin by nearest sub-segment (arc-length parameter).
4. **Majority-vote smoothing** (2–3 passes over neighbors) removes speckle.
5. Write groups with `vg.add(indices, 1.0, 'REPLACE')`; bind with an Armature modifier (no auto weights — groups are already correct):
   ```python
   mod = obj.modifiers.new("Armature", 'ARMATURE'); mod.object = rig; obj.parent = rig
   ```

### ALWAYS color-debug the weights and render
Bake the assignment into a color attribute and view with an emission material — this is how you *see* leaks that a textured render hides:
```python
attr = me.color_attributes.get("SegDebug") or me.color_attributes.new("SegDebug", 'FLOAT_COLOR', 'POINT')
cols = np.ones((n, 4), np.float32)
for j, c in enumerate(COLORS): cols[final == j, :3] = c
attr.data.foreach_set("color", cols.ravel())
# emission material reading the "SegDebug" attribute → render → Read → find the leak
```
Then a **stress-test pose**: rotate a bone to its motion extreme with the real texture and render — confirms panels don't tear and boundaries fall on the actual joint. A boundary that bisects a ball joint opens a gap when rotated; move boundaries by **arc-length** so each ball stays wholly on one bone (socket behavior: ball stays put, next part rotates around it).

## "Weight paint via MCP"

Pincel gesture isn't reachable, but weight *editing* is — and for mech it's better than a brush:
- Region reassignment by rule (the BFS/arc-length approach above), shown via color-debug before committing.
- Per-part **vertex groups as selection sets** (below) for the user to Select in Edit mode.
For genuinely soft blends (hoses, cables) the user still uses the in-Blender Blur brush; everything else, do it numerically.

## Bonus: a vertex group per mechanical part (doesn't break animation)

Extra vertex groups whose names don't match a bone are **inert to deformation** — the Armature modifier only reads groups named like a bone. So you can add `part.FL.03_elbow_ball`, `part.FL.05_knee_hub`, etc. as selection sets / future-bone candidates without touching the animation. Detect part boundaries from the width profile ("waists") along each leg's arc-length. Verify the deform groups (`coxa.*`, `femur.*`, `shin.*`, `body`) are still intact afterward.
