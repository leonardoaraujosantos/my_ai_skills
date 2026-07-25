# Modeling, "Sculpt" via Code, Materials, UV

## Procedural blockout → single sculpt surface

"Sculpting" through MCP means procedural mesh ops that read as sculpted, not brush strokes. The reliable pattern that produced a clean robot from primitives:

1. **Blockout** with primitives posed as body parts (spheres, cylinders). Use `bpy.ops.mesh.primitive_*_add`, set `scale`/`location`/`rotation_euler`.
2. **Join** them into one object: select all parts + a base, `bpy.context.view_layer.objects.active = base`, `bpy.ops.object.join()`, then `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)`.
3. **Voxel remesh** to weld intersecting primitives into one continuous surface — this is what makes it sculptable and clean:
   ```python
   obj.data.remesh_voxel_size = 0.02      # smaller = finer, denser, slower
   bpy.ops.object.voxel_remesh()
   bpy.ops.object.shade_smooth()
   ```
4. **Light smoothing** so primitive intersections read as clay, not hard CSG seams:
   ```python
   sm = obj.modifiers.new("Soften", 'SMOOTH'); sm.factor = 0.5; sm.iterations = 3
   bpy.ops.object.modifier_apply(modifier="Soften")
   ```

**Failure modes seen:** over-smoothing (`factor 0.6, iterations 6`) melted thin parts (antenna vanished, arms absorbed) — keep smoothing gentle. Primitives that only touch, not overlap, leave disconnected islands after remesh. **Verify one connected island** by walking the edge graph:
```python
# union-find or BFS over me.edges; assert len(visited) == len(me.vertices)
```
If arms come out detached from the torso, add bridging spheres at the shoulders before joining.

Iterate visually: render between attempts. Three render-checked iterations turned a failed blob into a clean mesh.

## Materials: shader-node trees are fully scriptable

Build node trees node-by-node. Pattern (procedural grass, verified in-scene):
```python
mat = bpy.data.materials.new("Grass"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
out  = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 45
ramp  = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.02, 0.11, 0.025, 1)
ramp.color_ramp.elements[1].color = (0.075, 0.28, 0.06, 1)
nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
obj.data.materials.clear(); obj.data.materials.append(mat)
```
The only thing lost vs. the editor is node *layout* (positions are code coords, cosmetic). Node groups, Voronoi/noise/musgrave, bump/normal, mix nodes — all scriptable. To swap for a debug material and back, keep the original name (`obj.data.materials["Material.001"]`) and re-append it.

### Baking a texture to exactly match the UV

For a regulation pattern that must align with the UV (e.g. a soccer ball's truncated-icosahedron: 12 pentagons + 20 hexagons), don't fight Voronoi randomness — **compute the pattern into an equirectangular image** sized to the UV sphere's unwrap, using numpy, then pack it:
```python
import numpy as np
W, H = 2048, 1024
img = bpy.data.images.new("Pattern", W, H, alpha=False)
img.pixels.foreach_set(rgba.ravel())   # rgba: (H*W, 4) float32
img.pack()
```
Feed it through a `ShaderNodeTexImage` on `Object`/`UV` coords. A companion non-color height image + `ShaderNodeBump` gives recessed seams. Because it rides the UVs, the pattern deforms with squash/stretch automatically. When a pattern looks wrong, **save the flat image and Read it** — that exposed a rotated-coordinate bug that renders alone hid.

## UV

All unwraps are scriptable but need correct context (Edit mode + selection): `bpy.ops.uv.smart_project`, `bpy.ops.uv.unwrap`, cube/cylinder/sphere project, `bpy.ops.uv.pack_islands`, lightmap pack. Mark seams procedurally (by angle, by sharp edges) and manipulate `mesh.uv_layers` data directly (move/scale islands numerically). For game props, `smart_project` + `pack_islands` with margin covers ~90%. What is NOT possible: freehand dragging of a UV island in the editor — that's a brush gesture. Verify by rendering the UV editor via the OpenGL-render trick.

## Particle grass and reactive effects

Hair particle systems make fur/grass at render density; drive blade **length** from a vertex group, and drive that group from proximity to another object for reactive flattening:
```python
vwp = ground.modifiers.new("BallProximity", 'VERTEX_WEIGHT_PROXIMITY')
vwp.vertex_group = "GrassFlatten"; vwp.target = ball
vwp.proximity_mode = 'GEOMETRY'; vwp.proximity_geometry = {'FACE'}
vwp.min_dist = 0.03; vwp.max_dist = 0.9; vwp.falloff_type = 'SMOOTH'
# order this modifier BEFORE the particle system in the stack; then:
ground.particle_systems[-1].vertex_group_length = "GrassFlatten"
```
This re-evaluates per frame with zero baking — grass presses down under a moving object and springs back.
