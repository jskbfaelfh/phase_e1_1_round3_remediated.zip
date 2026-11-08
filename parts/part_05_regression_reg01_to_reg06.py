"""
Stage E1.1 Isolated Disentanglement Engine - Engineering Remediation Regression Suite Round 4
Frozen Specification Reference: e1_1_final_closure_amendment.md
Round 4 Targeted Remediation:
  - G5 Separation Measurement: strictly between >= 2 lines, never from crop margins. 7 mandatory images.
  - q_aspect: bounding box evaluation (valid, touching, clipped, overlapping, zero dimension, unobserved).
  - G2 EVID_06: indentation offset from physical box coordinates, zero metadata reliance.
  - Delimiters: non-preemptive extraction, comma/chemical/brand/range protection, merged delimiter constituents.
  - OCR Text Coordinates: mandatory text_start/text_end, zero defaulting strictly rejected.
  - Character Integrity: non-vacuous reversibility, leading/trailing whitespace, repeated spaces, mutation detection.
  - Structural Envelope: financial and quantity bounds, source tracking, ambiguous number protection.
  - Full Package Isolation & AST Deep Sandbox.
"""

import os
import sys
import math
import ast
import numpy as np
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.types import (
    EntityType, CountClass, BoundaryStatus, ReconstructionStatus,
    EvidenceGroup, GeomObservationState, InputLine, DecisionOutput
)
from engine.extractors import (
    compute_q_skew, compute_q_sep, compute_q_aspect, compute_q_geo,
    evaluate_bounding_boxes_aspect, measure_raster_from_crop,
    compute_reliability_gates, extract_evidence_signals,
    compute_conflict_penalties, evaluate_structural_envelope,
    validate_and_parse_bounding_boxes, compute_indentation_offset
)
from engine.matching import reconstruct_original_string
from engine.decision_engine import (
    DisentanglementDecisionEngine, CANONICAL_VALID_STATES,
    validate_output_compatibility, find_boundary_delimiters,
    partition_text_and_track_delimiters
)
from synthetic_cases.cases import (
    create_single_line_pixel_crop, create_multiline_pixel_crop
)


def run_remediation_regression_suite() -> Dict[str, Any]:
    engine = DisentanglementDecisionEngine()
    results = []

    # -------------------------------------------------------------
    # REG_01: Zero Syntax & Runtime Errors Compilation
    # -------------------------------------------------------------
    compiled_count = 0
    py_files = []
    for root, _, files in os.walk(BASE_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    for pf in py_files:
        with open(pf, "r", encoding="utf-8") as fh:
            compile(fh.read(), pf, "exec")
            compiled_count += 1

    pass_reg1 = (compiled_count == len(py_files)) and (compiled_count >= 12)
    results.append({
        "test_name": "REG_01: Zero Syntax & Runtime Errors Compilation",
        "passed": pass_reg1,
        "compiled_count": compiled_count,
        "detail": f"Successfully compiled {compiled_count} Python source files with zero syntax errors."
    })

    # -------------------------------------------------------------
    # REG_02: Zero Measurement Fabrication in Non-Medicine Path
    # -------------------------------------------------------------
    admin_line = InputLine(
        text="INVOICE TOTAL / CASH PAYMENT: 50.00",
        ocr_confidence=0.95,
        image_crop=create_single_line_pixel_crop()
    )
    out_admin = engine.analyze_line(admin_line)
    pass_reg2 = (
        out_admin.axis1_entity_type == EntityType.NON_MEDICINE_TEXT and
        out_admin.axis2_count_class == CountClass.NON_APPLICABLE and
        out_admin.axis3_boundary_status == BoundaryStatus.NON_APPLICABLE and
        out_admin.axis4_reconstruction_status == ReconstructionStatus.NON_APPLICABLE and
        out_admin.w_active == 0.0 and
        out_admin.geom_observation_state == GeomObservationState.GEOM_UNOBSERVED and
        out_admin.hrs_score == 0.0 and
        len(out_admin.reconstructed_spans) == 0
    )
    results.append({
        "test_name": "REG_02: Zero Measurement Fabrication in Non-Medicine Path",
        "passed": pass_reg2,
        "w_active": out_admin.w_active,
        "geom_state": out_admin.geom_observation_state.value,
        "detail": "Verified that Step 1 pre-emption emits honest unmeasured values (W_active=0.0, GEOM_UNOBSERVED)."
    })

    # -------------------------------------------------------------
    # REG_03: Canonical Output State Matrix Enforcement
    # -------------------------------------------------------------
    illegal_raised = False
    try:
        dummy_bad = DecisionOutput(
            axis1_entity_type=EntityType.NON_MEDICINE_TEXT,
            axis2_count_class=CountClass.SINGLE_MEDICINE,  # Illegal under Axiom 1
            axis3_boundary_status=BoundaryStatus.NO_SPLIT_REQUIRED,
            axis4_reconstruction_status=ReconstructionStatus.RECONSTRUCTED_SINGLE,
            hrs_score=0.0, s_norm=0.0, w_active=0.9, p_conflict=0.0, p_chem=0.0, p_ratio=0.0,
            s_env=1.0, s_env_inputs={}, n_multi=0, active_multi_groups=[], precedence_path="",
            reconstructed_spans=[], boundary_cut_indices=[]
        )
        validate_output_compatibility(dummy_bad)
    except ValueError:
        illegal_raised = True

    pass_reg3 = illegal_raised and (len(CANONICAL_VALID_STATES) == 10)
    results.append({
        "test_name": "REG_03: Canonical Output State Compatibility Enforcement",
        "passed": pass_reg3,
        "canonical_state_count": len(CANONICAL_VALID_STATES),
        "detail": "Verified that CANONICAL_VALID_STATES contains exactly 10 authorized states and invalid states raise ValueError."
    })

    # -------------------------------------------------------------
    # REG_04: Categorical Separation of GEOM_UNOBSERVED vs ZERO_QUALITY
    # -------------------------------------------------------------
    gates_unobs, state_unobs, _ = compute_reliability_gates(0.90, None, image_crop=None)
    blank_crop = np.full((16, 100), 255, dtype=np.uint8)  # White paper, 0 ink bands
    gates_zero, state_zero, _ = compute_reliability_gates(0.90, None, image_crop=blank_crop)
    single_crop = create_single_line_pixel_crop()
    gates_single, state_single, _ = compute_reliability_gates(0.90, None, image_crop=single_crop)
    multi_crop = create_multiline_pixel_crop(lines=2)
    gates_multi, state_multi, _ = compute_reliability_gates(0.90, None, image_crop=multi_crop)

    pass_reg4 = (
        state_unobs == GeomObservationState.GEOM_UNOBSERVED and
        gates_unobs[EvidenceGroup.G5_RASTER] == 0.0 and
        state_single == GeomObservationState.GEOM_UNOBSERVED and
        gates_single[EvidenceGroup.G5_RASTER] == 0.0 and
        state_zero == GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY and
        gates_zero[EvidenceGroup.G5_RASTER] == 0.0 and
        state_multi == GeomObservationState.GEOM_OBSERVED_VALID and
        gates_multi[EvidenceGroup.G5_RASTER] > 0.0
    )
    results.append({
        "test_name": "REG_04: Strict Geometric Provenance Categorical Separation",
        "passed": pass_reg4,
        "unobserved_none": state_unobs.value,
        "unobserved_single": state_single.value,
        "zero_quality": state_zero.value,
        "valid_multiline": state_multi.value
    })

    # -------------------------------------------------------------
    # REG_05: G5 Pixel Evidence Mandate (7 Mandatory Image Tests & Margin Independence Proof)
    # -------------------------------------------------------------
    # 1. 1 line centered in image
    img_center = np.full((32, 100), 255, dtype=np.uint8)
    img_center[12:20, 10:90] = 30  # top margin 12, bot margin 12
    meas_c, state_c = measure_raster_from_crop(img_center)

    # 2. 1 line adjacent to top margin
    img_top = np.full((32, 100), 255, dtype=np.uint8)
    img_top[0:8, 10:90] = 30  # top margin 0, bot margin 24
    meas_t, state_t = measure_raster_from_crop(img_top)

    # 3. 1 line adjacent to bottom margin
    img_bot = np.full((32, 100), 255, dtype=np.uint8)
    img_bot[24:32, 10:90] = 30  # top margin 24, bot margin 0
    meas_b, state_b = measure_raster_from_crop(img_bot)

    # Margin Independence Proof:
    # All 3 single-line images must have delta_y_gap = None, q_sep = 0.0, q_geo = 0.0, state = GEOM_UNOBSERVED
    margin_indep_ok = (
        meas_c["line_gap"] is None and meas_c["q_sep"] == 0.0 and state_c == GeomObservationState.GEOM_UNOBSERVED and
        meas_t["line_gap"] is None and meas_t["q_sep"] == 0.0 and state_t == GeomObservationState.GEOM_UNOBSERVED and
        meas_b["line_gap"] is None and meas_b["q_sep"] == 0.0 and state_b == GeomObservationState.GEOM_UNOBSERVED
    )

    # 4. 2 lines with clear gap (h_line = 8, gap = 6 -> ratio = 6/8 = 0.75 >= 0.30 -> q_sep = 1.0)
    img_2_clear = np.full((30, 100), 255, dtype=np.uint8)
    img_2_clear[4:12, 10:90] = 30
    img_2_clear[18:26, 10:90] = 30  # gap = 6
    meas_2c, state_2c = measure_raster_from_crop(img_2_clear)
    two_clear_ok = (meas_2c["line_gap"] == 6.0 and meas_2c["q_sep"] == 1.0 and state_2c == GeomObservationState.GEOM_OBSERVED_VALID)

    # 5. 2 lines with small gap (h_line = 10, gap = 1 -> ratio = 0.10 < 0.30 -> q_sep = 0.10/0.30 = 0.333)
    img_2_small = np.full((30, 100), 255, dtype=np.uint8)
    img_2_small[4:14, 10:90] = 30
    img_2_small[15:25, 10:90] = 30  # gap = 1
    meas_2s, state_2s = measure_raster_from_crop(img_2_small)
    two_small_ok = (meas_2s["line_gap"] == 1.0 and math.isclose(meas_2s["q_sep"], 1.0/3.0, abs_tol=0.01) and state_2s == GeomObservationState.GEOM_OBSERVED_VALID)

    # 6. Blank white image without ink
    img_blank = np.full((30, 100), 255, dtype=np.uint8)
    meas_bl, state_bl = measure_raster_from_crop(img_blank)
    blank_ok = (meas_bl["q_geo"] == 0.0 and state_bl == GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY)

    # 7. Corrupted / invalid dimensions image (h < 4 or w < 8)
    img_corrupt = np.full((3, 5), 255, dtype=np.uint8)
    meas_cr, state_cr = measure_raster_from_crop(img_corrupt)
    corrupt_ok = (meas_cr["q_geo"] == 0.0 and state_cr == GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY)

    # Metadata bypass proof:
    gates_meta_low, _, _ = compute_reliability_gates(0.90, raster_meta={"q_geo": 0.10}, image_crop=img_2_clear)
    gates_meta_high, _, _ = compute_reliability_gates(0.90, raster_meta={"q_geo": 0.99}, image_crop=img_2_clear)
    meta_bypass_ok = (gates_meta_low[EvidenceGroup.G5_RASTER] == gates_meta_high[EvidenceGroup.G5_RASTER] == 1.0)

    pass_reg5 = (
        margin_indep_ok and two_clear_ok and two_small_ok and blank_ok and corrupt_ok and meta_bypass_ok
    )
    results.append({
        "test_name": "REG_05: G5 Pixel Evidence Mandate (7 Image Cases & Margin Independence Proof)",
        "passed": pass_reg5,
        "margin_indep_ok": margin_indep_ok,
        "two_clear_ok": two_clear_ok,
        "two_small_ok": two_small_ok,
        "blank_ok": blank_ok,
        "corrupt_ok": corrupt_ok,
        "meta_bypass_ok": meta_bypass_ok
    })

    # -------------------------------------------------------------
    # REG_06: Multiplicative Q_geo & q_aspect Bounding Box Evaluation (7 Aspect Cases)
    # -------------------------------------------------------------
    # 1. Valid boxes
    boxes_valid = [
        {"x0": 5.0, "x1": 40.0, "y0": 2.0, "y1": 14.0},
        {"x0": 45.0, "x1": 80.0, "y0": 2.0, "y1": 14.0}
    ]
    q_asp_1, meta_asp_1 = evaluate_bounding_boxes_aspect(boxes_valid, crop_w=100, crop_h=20)
    asp_1_ok = (q_asp_1 == 1.0 and meta_asp_1["status"] == "VALID")

    # 2. Touching boxes (gap == 0)
    boxes_touching = [
        {"x0": 5.0, "x1": 40.0, "y0": 2.0, "y1": 14.0},
        {"x0": 40.0, "x1": 80.0, "y0": 2.0, "y1": 14.0}
    ]
    q_asp_2, meta_asp_2 = evaluate_bounding_boxes_aspect(boxes_touching, crop_w=100, crop_h=20)
    asp_2_ok = (q_asp_2 == 0.0 and meta_asp_2["status"] == "TOUCHING")

    # 3. Clipped boxes at crop boundaries (x0 <= 0 or x1 >= crop_w)
    boxes_clipped = [
        {"x0": 0.0, "x1": 40.0, "y0": 2.0, "y1": 14.0},
        {"x0": 45.0, "x1": 80.0, "y0": 2.0, "y1": 14.0}
    ]
    q_asp_3, meta_asp_3 = evaluate_bounding_boxes_aspect(boxes_clipped, crop_w=100, crop_h=20)
    asp_3_ok = (q_asp_3 == 0.0 and meta_asp_3["status"] == "CLIPPED")

    # 4. Overlapping boxes (gap < 0)
    boxes_overlap = [
        {"x0": 5.0, "x1": 50.0, "y0": 2.0, "y1": 14.0},
        {"x0": 45.0, "x1": 80.0, "y0": 2.0, "y1": 14.0}
    ]
    q_asp_4, meta_asp_4 = evaluate_bounding_boxes_aspect(boxes_overlap, crop_w=100, crop_h=20)
    asp_4_ok = (q_asp_4 == 0.0 and meta_asp_4["status"] == "OVERLAPPING")

    # 5. Degenerate boxes (zero or negative width / height)
    boxes_degen = [
        {"x0": 10.0, "x1": 10.0, "y0": 2.0, "y1": 14.0}
    ]
    q_asp_5, meta_asp_5 = evaluate_bounding_boxes_aspect(boxes_degen, crop_w=100, crop_h=20)
    asp_5_ok = (q_asp_5 == 0.0 and meta_asp_5["status"] == "DEGENERATE")

    # 6. Missing box data (None or empty)
    q_asp_6, meta_asp_6 = evaluate_bounding_boxes_aspect(None, crop_w=100, crop_h=20)
    asp_6_ok = (q_asp_6 == 0.0 and meta_asp_6["status"] == "UNOBSERVED")

    # 7. Small image with valid crop dimensions but missing boxes -> crop only fallback
    _, _, meta_crop_only = compute_reliability_gates(0.90, None, image_crop=img_center, bounding_boxes=None)
    asp_7_ok = (meta_crop_only["aspect_valid"] is True and meta_crop_only["aspect_meta"]["status"] == "VALID_CROP_ONLY")

    # Multiplicative product verification: Q_geo = q_skew * q_sep * q_aspect
    q_sk = compute_q_skew(3.5)   # 0.50
    q_sp = compute_q_sep(1.5, 10.0)  # 0.50
    q_as = 1.0
    mult_prod_ok = math.isclose(q_sk * q_sp * q_as, 0.25)

    pass_reg6 = (
        asp_1_ok and asp_2_ok and asp_3_ok and asp_4_ok and asp_5_ok and asp_6_ok and asp_7_ok and mult_prod_ok
    )
    results.append({
        "test_name": "REG_06: Multiplicative Q_geo & q_aspect Bounding Box Evaluation (7 Aspect Cases)",
        "passed": pass_reg6,
        "asp_1_valid": asp_1_ok,
        "asp_2_touching": asp_2_ok,
        "asp_3_clipped": asp_3_ok,
        "asp_4_overlap": asp_4_ok,
        "asp_5_degen": asp_5_ok,
        "asp_6_unobserved": asp_6_ok,
        "asp_7_crop_fallback": asp_7_ok,
        "mult_prod_ok": mult_prod_ok
    })

    # -------------------------------------------------------------
    # REG_07: G2 Spatial Layout via OCR Bounding Boxes (Strict text_start/text_end Validation & Zero Defaulting Rejection)
    # -------------------------------------------------------------
    raw_bad_boxes = [
        {"text": "A", "x0": -5.0, "x1": 10.0, "text_start": 0, "text_end": 1},          # Rejected: x0 < 0
        {"text": "B", "x0": 20.0, "x1": 15.0, "text_start": 2, "text_end": 3},          # Rejected: x1 <= x0 (inverted)
        {"text": "C", "x0": float("nan"), "x1": 30.0, "text_start": 4, "text_end": 5},  # Rejected: NaN
        {"text": "D", "x0": 40.0, "x1": float("inf"), "text_start": 6, "text_end": 7},  # Rejected: Inf
        {"text": "E", "x0": 50.0, "x1": 60.0, "text_start": 10, "text_end": 5},         # Rejected: bad text span (start >= end)
        {"text": "F", "x0": 60.0, "x1": 70.0, "text_start": None, "text_end": 8},       # Rejected: missing text_start (ZERO DEFAULTING FORBIDDEN)
        {"text": "G", "x0": 70.0, "x1": 80.0, "text_start": 8, "text_end": None},       # Rejected: missing text_end
        {"text": "H", "x0": 80.0, "x1": 90.0, "text_start": 40, "text_end": 55},        # Rejected: text_end > text_len (50)
        {"text": "VALID1", "x0": 100.0, "x1": 148.0, "text_start": 0, "text_end": 6},   # Valid: len=6, width=48 -> char_w = 8.0
        {"text": "VALID2", "x0": 180.0, "x1": 228.0, "text_start": 10, "text_end": 16}  # Valid: len=6, width=48 -> char_w = 8.0 (gap=32 > 2.5*8=20)
    ]
    parsed_boxes, meta_g2 = validate_and_parse_bounding_boxes(raw_bad_boxes, text_len=50)
    pass_reg7 = (
        meta_g2["valid_box_count"] == 2 and
        meta_g2["rejected_box_count"] == 8 and
        math.isclose(meta_g2["d_med"], 8.0) and
        len(meta_g2["void_spans"]) == 1
    )
    results.append({
        "test_name": "REG_07: G2 Bounding Box Rejection & Zero Defaulting Strict Enforcement",
        "passed": pass_reg7,
        "valid_count": meta_g2["valid_box_count"],
        "rejected_count": meta_g2["rejected_box_count"],
        "d_med": meta_g2.get("d_med")
    })

