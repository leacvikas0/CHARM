# Working on CHARM

Read README.md, docs/METHODS.md, docs/DATA_FORMAT.md and docs/NEW_CHARACTER.md before changing the pipeline.

CHARM operates on already-retargeted animation. Do not add implicit Mixamo names, fixed clip lengths, unreviewed unit conversions or machine-specific paths to the reusable core. Treat generated rig roles as suggestions: `review_required` must be cleared after a real technical review.

Keep a single whole-body timing map. Timing variants sample complete accepted poses; no independent finger/foot retiming. Pose edits are restricted to explicit editable bones, with unselected local transforms and configured world transforms checked. Local protection does not imply world-space immobility when an ancestor changes.

The density map and curve/hold experiments are adaptations, not official reproductions of Tame–Tsume or MoNACA. Generic pose mixing is not a learned style model. Keep research citations and boundaries accurate.

Gesture events require an exact motion fingerprint, verified source windows and supporting evidence. Model descriptions/timestamps are proposals, not ground truth. Avoid added whole-body freezes around uncertain moving-support accents. Numerical invariants cannot establish artistic preference or contact/collision quality.

Put generated work under a new runs/ directory. Never overwrite a user's source scene or existing run. The public examples are original procedural data. Do not commit private motion, character assets, credentials, checkpoints, paper PDFs or local archives.

Verification:

```bash
python -m unittest discover -s tests
python scripts/demo.py --output runs/check_new
```

Use a new output folder on repeated demo runs. If changing the public synthetic input, regenerate its clip-bound event fingerprint and preview. Blender adapters require separate real-scene replay checks for their supported versions; unit tests alone do not verify arbitrary rigs or skinning.
