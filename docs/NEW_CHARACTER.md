# Use CHARM on another character

## Export accepted animation

Supply already-retargeted animation with correct rig/skin/fingers. The Blender exporter reads evaluated bones and scene fps and does not overwrite the source scene:

```bash
blender --factory-startup -b character.blend --python-exit-code 1 \
  -P blender/export_motion.py -- --armature CharacterRig \
  --start 1 --end 240 --output runs/new_clip/input.npz

charm template --input runs/new_clip/input.npz --output runs/new_clip/rig.json
```

Use your Blender executable path. Blender 5.2 was used during adapter development; the public synthetic demo does not require Blender. The exporter also writes source-frame metadata. On PowerShell, use single-line commands or its continuation syntax.

## Review and run

Review exact bone roles, up axis, units, motion-feature joints, editable bones and local/world protection. Set `review_required:false` after checking. Bone names can differ from common naming conventions; suggestions are not authoritative.

```bash
charm validate --input runs/new_clip/input.npz --config runs/new_clip/rig.json
charm run --input runs/new_clip/input.npz --config runs/new_clip/rig.json \
  --methods original twos density adaptive --output runs/new_clip/timing_01
```

Inspect original versus density first. Save the reviewed anchor list from the report back to the config for reproducible gesture work. Curve experiments additionally require a reviewed edit list. Outputs include one NPZ per method, timing maps, settings, audit metrics and source hashes. Output directories must be new.

## Optional gesture refinement

```bash
charm events-template --input runs/new_clip/input.npz --output runs/new_clip/events.json
```

Inspect actual neighboring frames in front/side views. Hand separation, chest-relative wrist paths and direction changes help locate candidates, but fastest movement is not automatically the meaningful pose. A projected overlap is not proof of contact; uncertain hops should not receive extra whole-body freezes. Fill the event file as described in DATA_FORMAT.

```bash
charm run --input runs/new_clip/input.npz --config runs/new_clip/rig.json \
  --events runs/new_clip/events.json --methods density gesture_subtle gesture_stronger \
  --output runs/new_clip/gesture_01
```

Reduce an infeasible edit budget instead of removing safety constraints. Never bypass a fingerprint mismatch by blindly replacing its hash.

## Bake and judge

```bash
blender --factory-startup -b character.blend --python-exit-code 1 \
  -P blender/bake_motion.py -- --motion runs/new_clip/gesture_01/gesture_subtle.npz \
  --armature CharacterRig --output runs/new_clip/baked_subtle
```

This saves a separate constant-key animation, reopens it, checks every integer frame and writes verification.json. Source-scene bind calibration/hierarchy must match. Inspect constraints or inherit-scale if replay fails rather than increasing tolerance to hide errors.

Add `--render --camera RenderCamera` to produce PNGs/MP4; ffmpeg must be on PATH. Use the same camera/light/materials across comparisons. No camera, character scene or texture is downloaded automatically. Matrix tolerance is measured in scene units.

Review full-speed loops and local windows for readability, pops, loss of bounce, lingering/hovering and intersections. New-mesh skinning and collision quality need actual geometry checks. Keep input, config, events, outputs and judgments together; a good result on one action does not establish a universal winner.
