# Motion data contract

Canonical NPZ files are loaded with `allow_pickle=False`:

| Array | Shape | Meaning |
|---|---|---|
| world | F×J×4×4 | Target-rig bone transforms in scene world coordinates |
| rest | J×4×4 | Bind transforms in the same coordinates |
| names | J strings | Unique exact bone names |
| parents | J integers | Parent indices; -1 for roots; acyclic; any joint order supported by core |
| fps | scalar | Frames per second |
| indices | optional F integers | Output-to-source indices in generated variants |

At least two frames are required. Transforms must be finite, nonsingular homogeneous matrices. A stored/configured fps conflict is rejected. Historical NPZ array names can be selected with `--key`; files without fps need an explicit fps value.

## Rig config

Generate with `charm template`, then review it. `review_required:false` records that technical review; it is not a substitute for one.

- `fps`, `meters_per_unit`, `up_axis`: explicit time/spatial conventions. Meters=1, centimeters=0.01. Input transforms are not silently rewritten.
- `roles`: exact hand/head/chest/foot names where available. Automatic density anchors need left_hand/right_hand; alternatively supply anchors_frames.
- `motion_joints`: bones contributing equally to displacement. Dense finger chains/accessories can dominate this measure if selected indiscriminately.
- `editable_joints`: explicit upper-body pose-edit list.
- `protected_joints`: explicit local protection; every unselected local transform is also protected.
- `world_protected_joints`: transforms that must not move before retiming, such as root/feet. An ancestor edit that moves these is rejected.
- `anchors_frames`: null for automatic proposals, or reviewed zero-based frame indices. Endpoints are included.
- `timing`: density strength and smoothing/anchor/hold durations in seconds; spatial prominence in meters. Uniform twos deliberately remains two output frames.
- `curve_tolerances_degrees`: per-editable-bone angular approximation tolerance.
- `pose_sources`: optional named aligned candidates. Paths are relative to the config; each entry specifies path, array key, strength and angle cap. A null cap is explicitly uncapped. Do not apply strength twice to an already-scaled external style clip.

Root edits are outside the pose-mixer scope. Protecting local palm/finger transforms does not prevent their world movement through edited shoulder/elbow ancestors.

## Event config

Create with `charm events-template`. Its canonical SHA256 covers numeric motion/rest data, hierarchy, names and fps. Storage compression or lossless dtype widening do not change the fingerprint when numeric values stay identical. A different motion is rejected even if its length matches.

Applied events require `verified:true`, `peak`, `end` (adjacent anchors), `delay` (source-frame budget), `rise` (output-frame count), `profiles` (`subtle`/`stronger`), `no_freeze_seconds` and supporting evidence. Empty events leave density unchanged. Do not transfer clip-specific delays/frame numbers to a new motion or fps without reviewing them.

Blender's matrix_basis is not a world rotation. The adapters account for bind orientation and armature object transforms, then verify replay. Different constraints/inherit-scale behavior can still require a rig-specific adapter.
