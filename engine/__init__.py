"""
Stage E1.1 Isolated Disentanglement Engine Package
"""

from .types import (
    EntityType, CountClass, BoundaryStatus, ReconstructionStatus,
    GeomObservationState, EvidenceGroup, InputLine, DecisionOutput
)
from .decision_engine import DisentanglementDecisionEngine
from .matching import (
    compute_span_iou, optimal_hungarian_matching, compute_span_metrics, compute_levenshtein
)

__all__ = [
    "EntityType",
    "CountClass",
    "BoundaryStatus",
    "ReconstructionStatus",
    "GeomObservationState",
    "EvidenceGroup",
    "InputLine",
    "DecisionOutput",
    "DisentanglementDecisionEngine",
    "compute_span_iou",
    "optimal_hungarian_matching",
    "compute_span_metrics",
    "compute_levenshtein"
]
