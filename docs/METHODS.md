# Methods and contribution boundaries

CHARM is a toolkit for controlled experiments on already-retargeted motion. It does not claim a new trained model or a complete implementation of the cited systems. See [REFERENCES](REFERENCES.md).

## Timing

**Original** is an identity source map. **Uniform twos** updates every two output frames and preserves the final source frame. It is a control, not an automatically improved animation.

**Density timing** sums selected joints' displacement, smooths it, divides by the mean, and forms positive inverse-density dwell weights:

```text
dwell = clip(max(relative_density, 0.08) ** (-strength), 0.35, 3.0)
```

Cumulative dwell is normalized independently between fixed anchors. Inverse interpolation produces an output-to-source time map, rounded to source-frame indices. This allocates more time to low-displacement poses while preserving duration, order and anchor times. Default strength is 0.85. Smoothing/anchor/hold durations are configured in seconds; spatial thresholds use meters_per_unit.

Automatic anchors use hand separation and mean world-up height extrema, prune nearby duplicates and subdivide long intervals. They are geometric proposals, not inferred meaning, audio beats or verified contacts. Explicit anchors support motions without those hand roles.

This is a simplified Tame–Tsume-inspired adaptation. CHARM does not implement the paper's full density equalization, signed-cubic scaling, variable-duration treatment or constrained smoothing optimizer.

**Adaptive holds** use short holds around anchors and more frequent updates in transitions. They preserve accepted articulated poses but can become too stepped for an action. Compare against both identity and density before choosing.

## Curve cleanup

Selected local transforms are decomposed into proper rotation and their remaining component. A worst-error split procedure adds source keys until piecewise SO(3) SLERP meets the configured angular tolerance. Translation/nonrotation components are preserved. Every unselected joint remains locally protected; configured world-protected joints are checked independently.

The curve/hold experiments are informed by MoNACA. CHARM does not implement its complete segmentation and viewpoint-selection system. A smaller approximation error is a numerical constraint, not a perceptual quality score.

## Gesture-aware timing

Verified events specify adjacent anchor bounds, a peak and a small delay budget. Integer dynamic programming approximates a shaped slower-exit target while bounding source steps and displacement. The endpoints stay fixed. Outside selected windows the density baseline remains unchanged.

The cost combines distance from the target map, a smaller baseline-deviation penalty and a source-step penalty. The initial no-freeze interval forbids repeated source frames around the selected accent; later portions can still contain repeats. This does not establish physical support or collision clearance.

Events are bound to canonical motion fingerprints. A video model may propose phrases, but actual source frames, measured motion features and support/visibility need checking. An anchor guarantees that a pose is visited, not enough exposure to make it readable. More exposure can also weaken bounce or create a sticky performance. Use a control rather than forcing a winner.

## Aligned pose mixing

The mixer compares local rotations of an accepted input and a candidate already aligned to the same target rig/timeline. It scales their relative SO(3) rotation and optionally caps its magnitude, applies only explicitly editable joints, then reconstructs world transforms. Unselected locals and configured protected world transforms are audited.

This is not learned style generation. To use a model such as STyMo, obtain/run it upstream, construct and validate the target-rig basis adapter, then provide an aligned candidate. Matching names alone does not prove matching calibration. CHARM rejects differences in names, hierarchy, bind matrices, fps or frame count.

## Practical limits

One common timing map samples root, limbs and fingers together. Timing still changes velocities/accelerations and can change perceived physical behavior. Frozen finger articulation does not eliminate hand/body intersections. No skinning repair, contact optimizer, cloth solver, view optimizer or collision objective is included.
