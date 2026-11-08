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
