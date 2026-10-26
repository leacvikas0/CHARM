# Character showcase

- `original-smooth.mp4`: accepted character motion with its original smooth timing.
- `density-retimed.mp4`: the same accepted poses sampled with the density timing map.
- `original-vs-density.mp4`: labeled side-by-side comparison, original left and density right. The same crop is applied to both clips so the character is easier to see.
- `original-vs-density.webp`: full-resolution, true-color looping preview, replacing the smaller palette-limited GIF; use the full-rate MP4 for judging timing. Browser playback can differ.
- `showcase.json`: input hashes and comparison framing metadata. The individual MP4s are copied byte-for-byte from the accepted results.

All MP4s are ten seconds, 300 frames at 30 fps, without audio. No new pose, material, lighting or camera treatment was applied to favor one side. The synthetic skeleton remains available separately as a reproducible code example.

These rendered videos were supplied by the project maintainer for demonstration. CHARM's MIT software license does not grant rights to the underlying character, motion or other source assets. No source character scene, texture or captured-motion dataset is included; contact the maintainer for media reuse questions.

The comparison can be rebuilt from maintainer-provided clips with `scripts/build_showcase.py` (optional OpenCV, Pillow and ffmpeg). It never downloads character assets.
