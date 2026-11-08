"""
Stage E1.1 Disentanglement Decision Engine - Core Decision Engine Implementation
Frozen Specification Reference: e1_1_final_closure_amendment.md
Remediation Round 2
"""

from typing import Dict, Any, Tuple, List, Optional
from .types import (
    EntityType, CountClass, BoundaryStatus, ReconstructionStatus,
    EvidenceGroup, GeomObservationState, InputLine, DecisionOutput,
    GroupEvaluation
)
from .extractors import (
    detect_non_medicine_entity, compute_reliability_gates,
    extract_evidence_signals, compute_conflict_penalties,
    evaluate_structural_envelope
)


# Base Engineering Weights (Sum = 1.00)
BASE_WEIGHTS: Dict[EvidenceGroup, float] = {
    EvidenceGroup.G1_SYNTACTIC: 0.30,
    EvidenceGroup.G2_SPATIAL: 0.25,
    EvidenceGroup.G3_ENVELOPE: 0.20,
    EvidenceGroup.G4_FINANCIAL: 0.15,
    EvidenceGroup.G5_RASTER: 0.10
}

# Capacity Noise Floor (Strictly frozen at 0.30)
TAU_ACTIVE_FLOOR = 0.30

# Canonical Valid States (Authorized by Frozen Compatibility Matrix)
CANONICAL_VALID_STATES = {
    (EntityType.MEDICINE_ROW, CountClass.SINGLE_MEDICINE, BoundaryStatus.NO_SPLIT_REQUIRED, ReconstructionStatus.RECONSTRUCTED_SINGLE),
    (EntityType.MEDICINE_ROW, CountClass.MULTIPLE_MEDICINES, BoundaryStatus.DISENTANGLED_BOUNDARY, ReconstructionStatus.RECONSTRUCTED_MULTI),
    (EntityType.MEDICINE_ROW, CountClass.PROVISIONAL_COUNT, BoundaryStatus.DISENTANGLED_BOUNDARY, ReconstructionStatus.PROVISIONAL_RECONSTRUCTION),
    (EntityType.MEDICINE_ROW, CountClass.PROVISIONAL_COUNT, BoundaryStatus.PROVISIONAL_BOUNDARY, ReconstructionStatus.PROVISIONAL_RECONSTRUCTION),
    (EntityType.MEDICINE_ROW, CountClass.PROVISIONAL_COUNT, BoundaryStatus.NO_SPLIT_REQUIRED, ReconstructionStatus.PROVISIONAL_RECONSTRUCTION),
    (EntityType.MEDICINE_ROW, CountClass.PROVISIONAL_COUNT, BoundaryStatus.ABSTAIN_UNSUPPORTED_BOUNDARY, ReconstructionStatus.ABSTAIN_SEGMENTATION),
    (EntityType.MEDICINE_ROW, CountClass.PROVISIONAL_COUNT, BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT, ReconstructionStatus.ABSTAIN_SEGMENTATION),
    (EntityType.MEDICINE_ROW, CountClass.ABSTAIN_COUNT, BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT, ReconstructionStatus.ABSTAIN_SEGMENTATION),
    (EntityType.NON_MEDICINE_TEXT, CountClass.NON_APPLICABLE, BoundaryStatus.NON_APPLICABLE, ReconstructionStatus.NON_APPLICABLE),
    (EntityType.AMBIGUOUS_TEXT, CountClass.ABSTAIN_COUNT, BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT, ReconstructionStatus.ABSTAIN_SEGMENTATION)
}


def validate_output_compatibility(output: DecisionOutput) -> None:
    """
    Validates that the output tuple matches one of the canonical valid states
    and violates none of the formal dependency axioms.
    """
    state_tuple = (
        output.axis1_entity_type,
        output.axis2_count_class,
        output.axis3_boundary_status,
        output.axis4_reconstruction_status
    )
    if state_tuple not in CANONICAL_VALID_STATES:
        raise ValueError(
            f"Output state compatibility violation: {state_tuple} is not a canonical valid state."
        )


def find_boundary_delimiters(text: str, signals: Dict[str, float], details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Finds candidate boundary split intervals (start, end) in the text string
    along with their exact classification and provenance group.
    Extracts ALL candidate delimiter types independently without preemption:
      1. Real newlines ('\\n') and escaped newlines ('\\\\n')
      2. Spaced hyphens / dashes (' - ')
      3. Slash separators (' / ' or isolated '/')
      4. Spatial voids from OCR bounding boxes
    Overlapping intervals are merged cleanly, combining types and sources.
    """
    raw_candidates: List[Dict[str, Any]] = []
    
    # 1. Real newlines
    for i, ch in enumerate(text):
        if ch == '\n':
            raw_candidates.append({
                "start": i, "end": i + 1,
                "text": "\n", "delimiter_type": "NEWLINE_DELIMITER",
                "source": "G5_RASTER"
            })
            
    # Escaped newlines
    if '\\n' in text:
        idx = text.find('\\n')
        while idx != -1:
            raw_candidates.append({
                "start": idx, "end": idx + 2,
                "text": "\\n", "delimiter_type": "ESCAPED_NEWLINE_DELIMITER",
                "source": "G5_RASTER"
            })
            idx = text.find('\\n', idx + 2)
            
    # 2. Spaced dash delimiter (e.g. ' - ')
    if details.get("dash_matches"):
        for start, end in details["dash_matches"]:
            raw_candidates.append({
                "start": start, "end": end,
                "text": text[start:end], "delimiter_type": "SPACED_HYPHEN_DELIMITER",
                "source": "G1_SYNTACTIC"
            })
            
    # 3. Slash delimiter (e.g. ' / ')
    if details.get("slash_matches"):
        for start, end in details["slash_matches"]:
            raw_candidates.append({
                "start": start, "end": end,
                "text": text[start:end], "delimiter_type": "SLASH_DELIMITER",
                "source": "G1_SYNTACTIC"
            })
            
    # 4. Whitespace void split from OCR bounding boxes
    if details.get("void_spans"):
        for start, end in details["void_spans"]:
            raw_candidates.append({
                "start": start, "end": end,
                "text": text[start:end], "delimiter_type": "SPATIAL_VOID_DELIMITER",
                "source": "G2_SPATIAL"
            })
            
    if not raw_candidates:
        return []

    # Sort strictly by start ascending, then end ascending
    sorted_candidates = sorted(raw_candidates, key=lambda c: (c["start"], c["end"]))

    # Initialize constituents for each candidate
    for c in sorted_candidates:
        c["constituents"] = [{
            "start": c["start"],
            "end": c["end"],
            "text": c["text"],
            "delimiter_type": c["delimiter_type"],
            "source": c["source"]
        }]

    # Merge overlapping or contiguous intervals
    merged: List[Dict[str, Any]] = []
    current = dict(sorted_candidates[0])

    for nxt in sorted_candidates[1:]:
        if nxt["start"] < current["end"]:
            # Overlap: extend boundary to maximum end
            new_end = max(current["end"], nxt["end"])
            current["end"] = new_end
            current["text"] = text[current["start"]:new_end]
            
            # Combine delimiter types
            cur_types = current["delimiter_type"].split("+")
            nxt_types = nxt["delimiter_type"].split("+")
            combined_types = list(dict.fromkeys(cur_types + nxt_types))
            current["delimiter_type"] = "+".join(combined_types)
            
            # Combine sources
            cur_sources = current["source"].split("+")
            nxt_sources = nxt["source"].split("+")
            combined_sources = list(dict.fromkeys(cur_sources + nxt_sources))
            current["source"] = "+".join(combined_sources)
            
            # Retain constituent records for full auditability
            current["constituents"] = current["constituents"] + nxt["constituents"]
        else:
            merged.append(current)
            current = dict(nxt)

    merged.append(current)
    return merged


def partition_text_and_track_delimiters(
    text: str,
    boundary_delimiters: List[Dict[str, Any]],
    recon_status: ReconstructionStatus
) -> Tuple[List[Tuple[int, int, str]], List[Dict[str, Any]]]:
    """
    Partitions raw text into reconstructed entity spans and excluded interstitial delimiters.
    Guarantees:
      1. Every single character in text is strictly accounted for.
      2. Excluded delimiters are logged with exact start/end, text, classification, and source.
      3. Reversible: interleaving entities and excluded delimiters reproduces the raw input text 100%.
    """
    if recon_status in (ReconstructionStatus.ABSTAIN_SEGMENTATION, ReconstructionStatus.NON_APPLICABLE):
        return [], []
        
    if recon_status == ReconstructionStatus.RECONSTRUCTED_SINGLE or not boundary_delimiters:
        # Check for leading / trailing whitespace
        stripped = text.strip()
        if not stripped:
            return [], []
        start = text.find(stripped)
        end = start + len(stripped)
        
        excluded = []
        if start > 0:
            excluded.append({
                "start": 0, "end": start,
                "text": text[0:start], "delimiter_type": "PADDING_WHITESPACE",
                "source": "TEXT_PADDING"
            })
        if end < len(text):
            excluded.append({
                "start": end, "end": len(text),
                "text": text[end:], "delimiter_type": "PADDING_WHITESPACE",
                "source": "TEXT_PADDING"
            })
        return [(start, end, stripped)], excluded

    # Multiple entities partitioned by boundary delimiters
    entity_spans: List[Tuple[int, int, str]] = []
    excluded_records: List[Dict[str, Any]] = []
    
    current_idx = 0
    for delim in boundary_delimiters:
        d_start = delim["start"]
        d_end = delim["end"]
        
        # Segment preceding this delimiter
        if d_start > current_idx:
            raw_seg = text[current_idx:d_start]
            stripped_seg = raw_seg.strip()
            if stripped_seg:
                # Find exact bounds of stripped entity within the segment
                rel_start = raw_seg.find(stripped_seg)
                seg_start = current_idx + rel_start
                seg_end = seg_start + len(stripped_seg)
                
                # Check for leading padding before entity
                if seg_start > current_idx:
                    excluded_records.append({
                        "start": current_idx, "end": seg_start,
                        "text": text[current_idx:seg_start],
                        "delimiter_type": "PADDING_WHITESPACE",
                        "source": "TEXT_PADDING"
                    })
                    
                entity_spans.append((seg_start, seg_end, stripped_seg))
                
                # Check for trailing padding after entity before delimiter
                if seg_end < d_start:
                    excluded_records.append({
                        "start": seg_end, "end": d_start,
                        "text": text[seg_end:d_start],
                        "delimiter_type": "PADDING_WHITESPACE",
                        "source": "TEXT_PADDING"
                    })
            else:
                # Entire preceding span was whitespace
                if raw_seg:
                    excluded_records.append({
                        "start": current_idx, "end": d_start,
                        "text": raw_seg,
                        "delimiter_type": "PADDING_WHITESPACE",
                        "source": "TEXT_PADDING"
                    })
                    
        # Log the boundary delimiter itself
        excluded_records.append(dict(delim))
        current_idx = d_end
        
    # Trailing segment after the last delimiter
    if current_idx < len(text):
        raw_seg = text[current_idx:]
        stripped_seg = raw_seg.strip()
        if stripped_seg:
            rel_start = raw_seg.find(stripped_seg)
            seg_start = current_idx + rel_start
            seg_end = seg_start + len(stripped_seg)
            
            if seg_start > current_idx:
                excluded_records.append({
                    "start": current_idx, "end": seg_start,
                    "text": text[current_idx:seg_start],
                    "delimiter_type": "PADDING_WHITESPACE",
                    "source": "TEXT_PADDING"
                })
                
            entity_spans.append((seg_start, seg_end, stripped_seg))
            
            if seg_end < len(text):
                excluded_records.append({
                    "start": seg_end, "end": len(text),
                    "text": text[seg_end:],
                    "delimiter_type": "PADDING_WHITESPACE",
                    "source": "TEXT_PADDING"
                })
        else:
            if raw_seg:
                excluded_records.append({
                    "start": current_idx, "end": len(text),
                    "text": raw_seg,
                    "delimiter_type": "PADDING_WHITESPACE",
                    "source": "TEXT_PADDING"
                })
                
    return entity_spans, sorted(excluded_records, key=lambda r: r["start"])


class DisentanglementDecisionEngine:
    """
    Stage E1.1 Isolated Multi-Medicine Disentanglement Decision Engine.
    Implements the Master HRS Equation, Hierarchical Gate Precedence, and State Matrix.
    Remediation Round 2.
    """
    def __init__(self):
        self.weights = dict(BASE_WEIGHTS)
        
    def analyze_line(self, line: InputLine) -> DecisionOutput:
        text = line.text
        reasons = []
        
        # -------------------------------------------------------------
        # STEP 1: Entity Type Gate (Pre-emption)
        # Defect B Fix: Zero measurement fabrication in non-medicine path!
        # W_active = 0.0, geom_state = GEOM_UNOBSERVED (honest unmeasured state).
        # -------------------------------------------------------------
        if detect_non_medicine_entity(text):
            reasons.append("Step 1: Administrative / Accounting non-medicine keywords detected.")
            output = DecisionOutput(
                axis1_entity_type=EntityType.NON_MEDICINE_TEXT,
                axis2_count_class=CountClass.NON_APPLICABLE,
                axis3_boundary_status=BoundaryStatus.NON_APPLICABLE,
                axis4_reconstruction_status=ReconstructionStatus.NON_APPLICABLE,
                hrs_score=0.0,
                s_norm=0.0,
                w_active=0.0,  # Honest unmeasured capacity: 0.0
                p_conflict=0.0,
                p_chem=0.0,
                p_ratio=0.0,
                s_env=0.0,
                s_env_inputs={},
                n_multi=0,
                active_multi_groups=[],
                precedence_path="Step 1: Entity Type Pre-emption",
                reconstructed_spans=[],
                boundary_cut_indices=[],
                excluded_delimiters=[],
                evidence_signals={},
                group_evaluations={},
                geom_observation_state=GeomObservationState.GEOM_UNOBSERVED,  # Honest unperformed state
                decision_reasons=reasons,
                input_text=text
            )
            validate_output_compatibility(output)
            return output
            
        entity_type = EntityType.MEDICINE_ROW
        
        # -------------------------------------------------------------
        # Signal Extraction and Quality Gates
        # -------------------------------------------------------------
        signals, details = extract_evidence_signals(line)
        gates, geom_state, g5_meta = compute_reliability_gates(
            line.ocr_confidence, line.raster_metadata, line.image_crop, line.bounding_boxes
        )
        
        # Group Scores S_m = max_{j in G_m}(e_j)
        s_1 = max(signals.get("EVID_01", 0.0), signals.get("EVID_02", 0.0), signals.get("EVID_03", 0.0), signals.get("EVID_04", 0.0))
        s_2 = max(signals.get("EVID_05", 0.0), signals.get("EVID_06", 0.0))
        s_3 = max(signals.get("EVID_07", 0.0), signals.get("EVID_08", 0.0), signals.get("EVID_09", 0.0))
        s_4 = max(signals.get("EVID_10", 0.0), signals.get("EVID_11", 0.0))
        s_5 = max(signals.get("EVID_12", 0.0), signals.get("EVID_13", 0.0))
        
        group_scores = {
            EvidenceGroup.G1_SYNTACTIC: float(s_1),
            EvidenceGroup.G2_SPATIAL: float(s_2),
            EvidenceGroup.G3_ENVELOPE: float(s_3),
            EvidenceGroup.G4_FINANCIAL: float(s_4),
            EvidenceGroup.G5_RASTER: float(s_5)
        }
        
        # Conflict penalties (Defect A Fix: compute_conflict_penalties)
        n_str = len(details.get("strengths", []))
        p_chem, p_ratio, p_conflict = compute_conflict_penalties(text, n_str)
        
        # Structural envelope
        s_env, s_env_inputs = evaluate_structural_envelope(text, details)
        
        # Calculate active measurement capacity W_active and evidence mass
        group_evals: Dict[str, GroupEvaluation] = {}
        raw_w_active = 0.0
        raw_e_mass = 0.0
        active_multi_groups = []
        
        for group, weight in self.weights.items():
            s_m = group_scores[group]
            gamma_m = gates[group]
            obs_state = "UNOBSERVED" if (group == EvidenceGroup.G5_RASTER and geom_state == GeomObservationState.GEOM_UNOBSERVED) else "OBSERVED"
            w_act = weight * gamma_m
            w_score = weight * s_m * gamma_m
            
            raw_w_active += w_act
            raw_e_mass += w_score
            
            # Multi-Facet Heuristic Corroboration condition: S_m * gamma_m >= 0.50
            if s_m * gamma_m >= 0.50:
                active_multi_groups.append(group.value)
                
            group_evals[group.value] = GroupEvaluation(
                group=group,
                score=round(s_m, 4),
                reliability=round(gamma_m, 4),
                observation_state=obs_state,
                base_weight=weight,
                weighted_score=round(w_score, 4),
                active_capacity=round(w_act, 4)
            )
            
        n_multi = len(active_multi_groups)
        
        # Unrounded Master HRS calculation
        # Safe zero-denominator handling: if raw_w_active < TAU_ACTIVE_FLOOR, Step 2 intercepts
        if raw_w_active >= TAU_ACTIVE_FLOOR:
            raw_s_norm = raw_e_mass / raw_w_active
            raw_hrs = max(0.0, raw_s_norm - p_conflict)
        else:
            raw_s_norm = 0.0
            raw_hrs = 0.0
            
        boundary_delims = find_boundary_delimiters(text, signals, details)
        cut_indices = [idx for d in boundary_delims for idx in (d["start"], d["end"])]
        
        # -------------------------------------------------------------
        # STEP 2: Capacity Noise Gate (W_active >= 0.30)
        # Strict unrounded float check: e.g. 0.299931 < 0.30 triggers ABSTAIN_COUNT
        # -------------------------------------------------------------
        if raw_w_active < TAU_ACTIVE_FLOOR:
            reasons.append(f"Step 2: Measurement capacity W_active ({raw_w_active:.6f}) < noise floor ({TAU_ACTIVE_FLOOR}).")
            output = DecisionOutput(
                axis1_entity_type=entity_type,
                axis2_count_class=CountClass.ABSTAIN_COUNT,
                axis3_boundary_status=BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT,
                axis4_reconstruction_status=ReconstructionStatus.ABSTAIN_SEGMENTATION,
                hrs_score=round(raw_hrs, 4),
                s_norm=round(raw_s_norm, 4),
                w_active=round(raw_w_active, 4),
                p_conflict=round(p_conflict, 4),
                p_chem=round(p_chem, 4),
                p_ratio=round(p_ratio, 4),
                s_env=round(s_env, 4),
                s_env_inputs=s_env_inputs,
                n_multi=n_multi,
                active_multi_groups=active_multi_groups,
                precedence_path="Step 2: Capacity Noise Gate",
                reconstructed_spans=[],
                boundary_cut_indices=[],
                excluded_delimiters=[],
                evidence_signals=signals,
                group_evaluations=group_evals,
                geom_observation_state=geom_state,
                decision_reasons=reasons,
                input_text=text
            )
            validate_output_compatibility(output)
            return output
            
        # -------------------------------------------------------------
        # STEP 3: Active Conflict Gate
        # -------------------------------------------------------------
        sum_multi_evidence = sum(group_scores[g] * gates[g] for g in EvidenceGroup)
        if sum_multi_evidence > 0.0 and p_conflict > 0.0:
            reasons.append(f"Step 3: Active conflict detected (Multi-evidence={sum_multi_evidence:.3f}, P_conflict={p_conflict:.3f}). Cannot certify without dictionary.")
            output = DecisionOutput(
                axis1_entity_type=entity_type,
                axis2_count_class=CountClass.PROVISIONAL_COUNT,
                axis3_boundary_status=BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT,
                axis4_reconstruction_status=ReconstructionStatus.ABSTAIN_SEGMENTATION,
                hrs_score=round(raw_hrs, 4),
                s_norm=round(raw_s_norm, 4),
                w_active=round(raw_w_active, 4),
                p_conflict=round(p_conflict, 4),
                p_chem=round(p_chem, 4),
                p_ratio=round(p_ratio, 4),
                s_env=round(s_env, 4),
                s_env_inputs=s_env_inputs,
                n_multi=n_multi,
                active_multi_groups=active_multi_groups,
                precedence_path="Step 3: Active Conflict Gate",
                reconstructed_spans=[],
                boundary_cut_indices=[],
                excluded_delimiters=[],
                evidence_signals=signals,
                group_evaluations=group_evals,
                geom_observation_state=geom_state,
                decision_reasons=reasons,
                input_text=text
            )
            validate_output_compatibility(output)
            return output
            
        # -------------------------------------------------------------
        # STEP 4: Definitive Multiplicity Gate
        # Corroborated via Multi-Facet Heuristic Corroboration across >= 2 groups
        # -------------------------------------------------------------
        if raw_hrs >= 0.70 and n_multi >= 2:
            reasons.append(f"Step 4: High HRS ({raw_hrs:.4f}) corroborated via Multi-Facet Heuristic Corroboration across {n_multi} active groups ({active_multi_groups}).")
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(
                text, boundary_delims, ReconstructionStatus.RECONSTRUCTED_MULTI
            )
            output = DecisionOutput(
                axis1_entity_type=entity_type,
                axis2_count_class=CountClass.MULTIPLE_MEDICINES,
                axis3_boundary_status=BoundaryStatus.DISENTANGLED_BOUNDARY,
                axis4_reconstruction_status=ReconstructionStatus.RECONSTRUCTED_MULTI,
                hrs_score=round(raw_hrs, 4),
                s_norm=round(raw_s_norm, 4),
                w_active=round(raw_w_active, 4),
                p_conflict=round(p_conflict, 4),
                p_chem=round(p_chem, 4),
                p_ratio=round(p_ratio, 4),
                s_env=round(s_env, 4),
                s_env_inputs=s_env_inputs,
                n_multi=n_multi,
                active_multi_groups=active_multi_groups,
                precedence_path="Step 4: Definitive Multiplicity Gate",
                reconstructed_spans=reconstructed_spans,
                boundary_cut_indices=cut_indices,
                excluded_delimiters=excluded_delims,
                evidence_signals=signals,
                group_evaluations=group_evals,
                geom_observation_state=geom_state,
                decision_reasons=reasons,
                input_text=text
            )
            validate_output_compatibility(output)
            return output
            
        # -------------------------------------------------------------
        # STEP 5: Definitive Singleness Gate
        # Requires low HRS (< 0.30), cohesive envelope (S_env=1.0), zero multi-evidence, zero conflict, n_multi == 0
        # -------------------------------------------------------------
        if raw_hrs < 0.30 and s_env == 1.0 and sum_multi_evidence == 0.0 and p_conflict == 0.0 and n_multi == 0:
            reasons.append("Step 5: Low HRS, cohesive structural envelope (S_env=1.0), zero multi-evidence, zero conflict.")
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(
                text, [], ReconstructionStatus.RECONSTRUCTED_SINGLE
            )
            output = DecisionOutput(
                axis1_entity_type=entity_type,
                axis2_count_class=CountClass.SINGLE_MEDICINE,
                axis3_boundary_status=BoundaryStatus.NO_SPLIT_REQUIRED,
                axis4_reconstruction_status=ReconstructionStatus.RECONSTRUCTED_SINGLE,
                hrs_score=round(raw_hrs, 4),
                s_norm=round(raw_s_norm, 4),
                w_active=round(raw_w_active, 4),
                p_conflict=round(p_conflict, 4),
                p_chem=round(p_chem, 4),
                p_ratio=round(p_ratio, 4),
                s_env=round(s_env, 4),
                s_env_inputs=s_env_inputs,
                n_multi=n_multi,
                active_multi_groups=active_multi_groups,
                precedence_path="Step 5: Definitive Singleness Gate",
                reconstructed_spans=reconstructed_spans,
                boundary_cut_indices=[],
                excluded_delimiters=excluded_delims,
                evidence_signals=signals,
                group_evaluations=group_evals,
                geom_observation_state=geom_state,
                decision_reasons=reasons,
                input_text=text
            )
            validate_output_compatibility(output)
            return output
            
        # -------------------------------------------------------------
        # STEP 6: Residual Provisional State
        # -------------------------------------------------------------
        reasons.append("Step 6: Intermediate evidence capacity; delegated to clinical review.")
        
        has_newline = '\n' in text or '\\n' in text
        has_void = bool(signals.get("EVID_05", 0.0) >= 0.50)
        has_stacked_raster = bool(signals.get("EVID_12", 0.0) >= 0.50)
        
        if (has_newline or has_stacked_raster) and boundary_delims:
            boundary_status = BoundaryStatus.PROVISIONAL_BOUNDARY if line.ocr_confidence < 0.75 else BoundaryStatus.DISENTANGLED_BOUNDARY
            recon_status = ReconstructionStatus.PROVISIONAL_RECONSTRUCTION
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(text, boundary_delims, recon_status)
        elif has_void and boundary_delims:
            boundary_status = BoundaryStatus.DISENTANGLED_BOUNDARY
            recon_status = ReconstructionStatus.PROVISIONAL_RECONSTRUCTION
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(text, boundary_delims, recon_status)
        elif boundary_delims:
            boundary_status = BoundaryStatus.PROVISIONAL_BOUNDARY if line.ocr_confidence < 0.75 else BoundaryStatus.DISENTANGLED_BOUNDARY
            recon_status = ReconstructionStatus.PROVISIONAL_RECONSTRUCTION
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(text, boundary_delims, recon_status)
        elif s_env == 0.0 and sum_multi_evidence == 0.0:
            # Bare unanchored token (e.g. ASPIRIN)
            boundary_status = BoundaryStatus.NO_SPLIT_REQUIRED
            recon_status = ReconstructionStatus.PROVISIONAL_RECONSTRUCTION
            reconstructed_spans, excluded_delims = partition_text_and_track_delimiters(text, [], recon_status)
        else:
            # Fused text with repeated patterns but zero spatial cut (e.g. CATAFLAM50MGVOLTAREN100MG)
            boundary_status = BoundaryStatus.ABSTAIN_UNSUPPORTED_BOUNDARY
            recon_status = ReconstructionStatus.ABSTAIN_SEGMENTATION
            reconstructed_spans = []
            excluded_delims = []
            
        output = DecisionOutput(
            axis1_entity_type=entity_type,
            axis2_count_class=CountClass.PROVISIONAL_COUNT,
            axis3_boundary_status=boundary_status,
            axis4_reconstruction_status=recon_status,
            hrs_score=round(raw_hrs, 4),
            s_norm=round(raw_s_norm, 4),
            w_active=round(raw_w_active, 4),
            p_conflict=round(p_conflict, 4),
            p_chem=round(p_chem, 4),
            p_ratio=round(p_ratio, 4),
            s_env=round(s_env, 4),
            s_env_inputs=s_env_inputs,
            n_multi=n_multi,
            active_multi_groups=active_multi_groups,
            precedence_path="Step 6: Residual Provisional State",
            reconstructed_spans=reconstructed_spans,
            boundary_cut_indices=cut_indices,
            excluded_delimiters=excluded_delims,
            evidence_signals=signals,
            group_evaluations=group_evals,
            geom_observation_state=geom_state,
            decision_reasons=reasons,
            input_text=text
        )
        validate_output_compatibility(output)
        return output
