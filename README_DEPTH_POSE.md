# Depth & Pose Estimator v0.5

Monocular, uncertainty-aware module between Shape Graph/Profile Fitter and Crochet Geometry Engine.

Pipeline:

`photo + ShapeGraph -> silhouette -> relative depth -> local pose -> visibility/occlusion -> ShapeGraph metadata -> Geometry Engine`

## What it estimates

- relative depth per piece;
- yaw/pitch/roll cues;
- visibility and occlusion score;
- image anchor and apparent width;
- confidence and warnings.

## Important limitation

A single RGB photograph does not contain enough information to recover true metric depth. The module therefore reports **relative depth** and explicitly stores uncertainty. For production, it is designed to accept future `depth_hint`, `image_anchor_px`, `image_span_px`, or a second camera view from the multimodal model.

## Integration

`compile_graph()` now runs:

1. Shape Graph validation
2. Profile Fitter
3. Depth & Pose Estimator
4. Crochet Geometry Engine
5. Pattern + assembly

The API result contains `depth_pose`, while each ShapeNode receives `metadata.depth_pose`, `estimated_depth_cm`, `visibility`, and `occlusion`.
