# Procedural Animation & NLA Clips

Robots and props are often *better* animated procedurally than hand-keyed — sine-based cycles loop perfectly, and the "mechanical" quality is a feature, not a flaw.

## The rotation math: author in world space, convert to bone space

Posing a bone by a world-space rotation and converting into its local rest frame avoids fighting per-bone axis orientation (the thing that makes hand-authoring bone rotations painful). Precompute each bone's rest basis once:
```python
rest = {b.name: rig.data.bones[b.name].matrix_local.to_3x3() for b in pb}
def world_rot(bone_name, R_world):        # R_world: mathutils.Matrix 3x3
    M = rest[bone_name]
    return (M.inverted() @ R_world @ M).to_quaternion()
# usage:
pb[f"femur.{q}"].rotation_quaternion = world_rot(f"femur.{q}", Matrix.Rotation(angle, 3, axis))
pb[f"femur.{q}"].keyframe_insert("rotation_quaternion", frame=f)
```
For a body translation authored in world space, use `M_body_inv = rest["body"].inverted()` and set `pb["body"].location = M_body_inv @ world_vec`.

Set `b.rotation_mode = 'QUATERNION'` on posed bones. **Key one extra frame past the cycle end (frame N+1 = frame 1)** for a seamless loop.

## Gaits

- **Trot** (fast, light): diagonal pairs in phase — `PHASE = {"FL":0, "RR":0, "FR":pi, "RL":pi}`. Two feet down.
- **Lateral-sequence walk** (heavy, realistic): one foot at a time, `OFFSET = {"RL":0.0, "FL":0.75, "RR":0.5, "FR":0.25}`, three feet always down. This reads as a heavy machine.

### What makes a walk look *real* (not a metronome)
1. **Asymmetric stance/swing.** Foot plants ~75% of the cycle pushing slowly, returns fast in the air (25%). `DUTY = 0.75`; in stance move slowly, in swing use a `smoothstep` return and a `sin(pi*w)**1.2` lift bell (sharp attack = firm step).
2. **Toe-off:** a small shin push at the end of stance.
3. **Weight transfer on the body:** sway toward the supported side, a small dip per footfall (`-0.016 * (0.5 - 0.5*cos(8*pi*t))` = 4 dips/cycle for a quadruped), subtle roll and pitch.
4. **Cadence:** slower = heavier. 48 frames @24fps (2s) reads as a deliberate mech; 32 frames is brisk.

Verify by evaluating `shin.<q>.tail.z` at sampled frames — confirm each foot lifts in its own window and feet don't all lift at once.

## Idle & death

- **Idle** (loop): hydraulic "breathing" — body up/down (~0.028), slight roll, micro-flex in the shins, feet planted. 72 frames.
- **Death** (one-shot): keyframe sparse extremes and let Bezier interpolation do the easing — recoil/jolt → legs give way (asymmetric splay per leg so it's not too mechanical) → belly hits ground → impact bounce → settle with final roll → power-off. The baked export converts the Bezier curves to per-frame samples, so the engine gets smooth motion without you tuning curves.

## Package multiple clips as NLA strips → one FBX with clips

Put each Action on its own NLA track; the FBX exporter with `bake_anim_use_nla_strips=True` writes each strip as a separate clip (Unity: clips in the import; Unreal: separate Animation Sequences).
```python
walk = ad.action                     # current action
tr = ad.nla_tracks.new(); tr.name = "walk"
tr.strips.new("QuadWalk", 1, walk); tr.mute = True
ad.action = None                     # clear so the next authoring pass starts clean
# ... author idle → push to an "idle" track, author die → "die" track ...
```
**Gotchas:**
- Authoring a new cycle while an Action is still active means its keys are overwritten — clear `ad.action = None` (and reset the pose) between cycles.
- In the viewport, **mute all NLA tracks** (`t.mute = True`) or the strips sum and the rig does all animations at once. Unmute exactly one to preview, and clear the active action (X in Action Editor) so it doesn't add on top.
- For export, unmute all tracks so every strip becomes a clip.
- Blender may create `Action.001` orphans; rename/remove to keep the clip list clean.

## Switching which animation plays (for the user, in Blender)
Reassign the Action in the **Action Editor** (Dope Sheet → Action Editor mode) and rebind the slot if needed (`references/setup.md` gotcha #3). Set the timeline End to match the clip (Walk 48, Idle 72, Die 60). If the rig sits in rest pose after assigning, it's the unbound action-slot — bind `ad.action_slot`.

**If the user "moves bones and nothing happens":** an active Action keys every bone every frame and overwrites manual poses — clear `ad.action = None` first. And if an IK layer exists, `ik_blend` at 0 means IK controls do nothing (see `rig-controls-export.md`).
