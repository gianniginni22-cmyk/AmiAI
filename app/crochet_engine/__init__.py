from .engine import (
    Gauge, ProfilePoint, PatternProject, RoundPlan, ShapePlan,
    compile_project, sphere_profile, egg_profile, tapered_profile,
    plan_profile, validate_project, distribute_delta,
)
from .profile_fitter import ProfileFitter, ProfileFitReport, NodeFit, ProfileObservation, MaskResult, fit_graph_to_image
from .depth_pose import DepthPoseEstimator, DepthPoseReport, PoseEstimate, estimate_depth_pose
from .shape_graph import (
    Vec3, Euler, ConnectionPoint, ShapeNode, ShapeEdge,
    GraphValidation, GraphPatternProject, ShapeGraph,
    dinosaur_shape_graph,
)

__all__ = [
    "Gauge", "ProfilePoint", "PatternProject", "RoundPlan", "ShapePlan",
    "compile_project", "sphere_profile", "egg_profile", "tapered_profile",
    "plan_profile", "validate_project", "distribute_delta",
    "Vec3", "Euler", "ConnectionPoint", "ShapeNode", "ShapeEdge",
    "GraphValidation", "GraphPatternProject", "ShapeGraph",
    "dinosaur_shape_graph",
    "DepthPoseEstimator", "DepthPoseReport", "PoseEstimate", "estimate_depth_pose",
    "ProfileFitter", "ProfileFitReport", "NodeFit", "ProfileObservation", "MaskResult", "fit_graph_to_image",
]

from .quality import QualityReport, assess_graph, construction_notes
from .pipeline import design_to_shape_graph, compile_design, select_technique
