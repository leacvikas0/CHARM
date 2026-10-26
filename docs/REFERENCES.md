# Research credits

CHARM is independent experimental software. It does not claim these methods as original research or imply endorsement by their authors.

## Pose-density retiming

Tomohiko Mukai, Hayato Okonogi, and Akinobu Maejima. **Pose-Density-Based Motion Retiming for Anime-Style Tame-Tsume.** SIGGRAPH Asia Technical Communications, 2026. [Author page](https://mukai-lab.org/publications/sa2026techcomm-tame-tsume/) · [DOI](https://doi.org/10.1145/3829339.3847839).

CHARM borrows the pose-density/timing motivation. Its positive inverse-density dwell map, fixed-duration intervals and integer source sampling are a simplified adaptation, not full reproduction of the paper's formulation. The author-hosted preprint is linked, not redistributed.

## Anime-like motion

Yui Koroku and Issei Fujishiro. **MoNACA: A System for Anime-like Motion Transfer by Adaptive Partitioning of Articular Trajectories.** The Journal of the Society for Art and Science, 23(3), 6_1–6_17, 2024. [Paper/DOI](https://doi.org/10.3756/artsci.23.6_1).

CHARM's bounded rotation-curve cleanup and selective-hold experiments are informed by this work. CHARM does not provide its complete segmentation or optimal-viewpoint system.

## Learned motion style

Jose Luis Ponton, Alexander Winkler, Ladislav Kavan, Yuting Ye, and Petr Kadlecek. **STyMo: Fast and Controllable Few-Shot Motion Style Transfer.** 2026. [Official repository](https://github.com/facebookresearch/STyMo) · [DOI](https://doi.org/10.1145/3811356).

The learned-style research informed integration experiments. This public repository supplies a generic target-aligned pose mixer, not STyMo's network, adapter, training data or checkpoints. Obtain upstream code separately. Validate the new target's skeleton/basis adapter before mixing model outputs.

## Citing CHARM

Use the repository's CITATION.cff for this software release. Cite the relevant original research alongside it; a software citation does not replace credit to the method authors. CHARM has no associated published paper or assigned DOI in this release.
