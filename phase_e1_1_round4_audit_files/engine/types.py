"""
Stage E1.1 Disentanglement Decision Engine - Type Definitions and State Grammar
Frozen Specification Reference: e1_1_final_closure_amendment.md
Remediation Round 2
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any


class EntityType(str, Enum):
    MEDICINE_ROW = "MEDICINE_ROW"
    NON_MEDICINE_TEXT = "NON_MEDICINE_TEXT"
    AMBIGUOUS_TEXT = "AMBIGUOUS_TEXT"


class CountClass(str, Enum):
    SINGLE_MEDICINE = "SINGLE_MEDICINE"
    MULTIPLE_MEDICINES = "MULTIPLE_MEDICINES"
    PROVISIONAL_COUNT = "PROVISIONAL_COUNT"
    ABSTAIN_COUNT = "ABSTAIN_COUNT"
    NON_APPLICABLE = "NON_APPLICABLE"


class BoundaryStatus(str, Enum):
    NO_SPLIT_REQUIRED = "NO_SPLIT_REQUIRED"
    DISENTANGLED_BOUNDARY = "DISENTANGLED_BOUNDARY"
    PROVISIONAL_BOUNDARY = "PROVISIONAL_BOUNDARY"
    ABSTAIN_UNSUPPORTED_BOUNDARY = "ABSTAIN_UNSUPPORTED_BOUNDARY"
    ABSTAIN_UNRESOLVED_CONFLICT = "ABSTAIN_UNRESOLVED_CONFLICT"
    NON_APPLICABLE = "NON_APPLICABLE"


class ReconstructionStatus(str, Enum):
    RECONSTRUCTED_SINGLE = "RECONSTRUCTED_SINGLE"
    RECONSTRUCTED_MULTI = "RECONSTRUCTED_MULTI"
    PROVISIONAL_RECONSTRUCTION = "PROVISIONAL_RECONSTRUCTION"
    ABSTAIN_SEGMENTATION = "ABSTAIN_SEGMENTATION"
    NON_APPLICABLE = "NON_APPLICABLE"


class GeomObservationState(str, Enum):
    GEOM_OBSERVED_VALID = "GEOM_OBSERVED_VALID"
    GEOM_OBSERVED_ZERO_QUALITY = "GEOM_OBSERVED_ZERO_QUALITY"
    GEOM_UNOBSERVED = "GEOM_UNOBSERVED"


class EvidenceGroup(str, Enum):
    G1_SYNTACTIC = "G1_SYNTACTIC"
    G2_SPATIAL = "G2_SPATIAL"
    G3_ENVELOPE = "G3_ENVELOPE"
    G4_FINANCIAL = "G4_FINANCIAL"
    G5_RASTER = "G5_RASTER"


@dataclass
class EvidenceSignal:
    id: str
    name: str
    group: EvidenceGroup
    raw_value: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroupEvaluation:
    group: EvidenceGroup
    score: float  # S_m in [0.0, 1.0]
    reliability: float  # gamma_m in [0.0, 1.0]
    observation_state: str  # OBSERVED or UNOBSERVED
    base_weight: float  # w_m
    weighted_score: float  # w_m * S_m * gamma_m
    active_capacity: float  # w_m * gamma_m
    active_signals: List[str] = field(default_factory=list)


@dataclass
class InputLine:
    text: str
    ocr_confidence: float = 0.90
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
    raster_metadata: Optional[Dict[str, Any]] = None
    image_crop: Optional[Any] = None  # 2D numpy array of image pixel intensities
    line_id: Optional[str] = None


@dataclass
class DecisionOutput:
    # 4 Output Axes
    axis1_entity_type: EntityType
    axis2_count_class: CountClass
    axis3_boundary_status: BoundaryStatus
    axis4_reconstruction_status: ReconstructionStatus
    
    # Mathematical Core Metrics
    hrs_score: float
    s_norm: float
    w_active: float
    p_conflict: float
    p_chem: float
    p_ratio: float
    
    # Gates and Sufficiency Metrics
    s_env: float
    s_env_inputs: Dict[str, Any]
    n_multi: int
    active_multi_groups: List[str]
    precedence_path: str
    
    # Reconstructed Entities and Cuts
    reconstructed_spans: List[Tuple[int, int, str]]
    boundary_cut_indices: List[int]
    excluded_delimiters: List[Dict[str, Any]] = field(default_factory=list)
    
    # Provenance and Traceability
    evidence_signals: Dict[str, float] = field(default_factory=dict)
    group_evaluations: Dict[str, GroupEvaluation] = field(default_factory=dict)
    geom_observation_state: GeomObservationState = GeomObservationState.GEOM_UNOBSERVED
    decision_reasons: List[str] = field(default_factory=list)
    input_text: str = ""
    
    def as_tuple(self) -> Tuple[str, str, str, str]:
        return (
            self.axis1_entity_type.value,
            self.axis2_count_class.value,
            self.axis3_boundary_status.value,
            self.axis4_reconstruction_status.value
        )
