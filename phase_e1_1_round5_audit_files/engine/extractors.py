"""
Stage E1.1 Disentanglement Decision Engine - Evidence Extractors and Physics Formulations
Frozen Specification Reference: e1_1_final_closure_amendment.md
Remediation Round 5:
  - G5: Strictly no q_aspect=1.0 from image crop dimensions alone; missing boxes -> GEOM_UNOBSERVED.
  - G5: evaluate_bounding_boxes_aspect groups boxes by line before checking horizontal overlap/touching.
  - G2: compute_indentation_offset: deleted fixed 16.0 threshold, deleted fixed 4.0 line threshold,
        requires valid d_med and valid Y coordinates, otherwise strictly UNOBSERVED.
  - G2: validate_and_parse_bounding_boxes: void_spans evaluated only between consecutive boxes on same line.
  - G1: Protects brand names with commas/hyphens, chemical formulas with plus, dosage ratios (160/12.5MG).
  - Character Conservation: Full provenance retention for merged delimiters.
"""

import math
import re
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .types import EvidenceGroup, GeomObservationState, InputLine


# -----------------------------------------------------------------------------
# Static Clinical & Linguistic Lexicons (Frozen Specifications)
# -----------------------------------------------------------------------------

STRENGTH_UNITS = r'\d+(?:\.\d+)?\s*(?:MG|G|GM|MCG|ML|IU|%|MG/ML)(?=[A-Z]|$|[^A-Za-z0-9])'

DOSAGE_FORMS = [
    r'\bTAB(?:LETS?)?\b', r'\bCAP(?:SULES?)?\b', r'\bSYR(?:UP)?\b',
    r'\bAMP(?:OULES?)?\b', r'\bVIAL\b', r'\bSUSP(?:ENSION)?\b',
    r'\bCREAM\b', r'\bOINT(?:MENT)?\b', r'\bDROPS?\b', r'\bSOL(?:UTION)?\b',
    r'\bINJ(?:ECTION)?\b', r'\bSUPP(?:OSITORY)?\b', r'\bSACHET\b'
]

PACKAGING_PATTERNS = [
    r'\b\d+\s*X\s*\d+\b', r'\b\d+\s*STRIPS?\b', r'\b\d+\s*TABS?\b',
    r'\bBOTTLE\b', r'\bPACK\b', r'\bBOX\b', r'\bBLISTER\b'
]

NON_MEDICINE_KEYWORDS = [
    r'\bTOTAL\b', r'\bSUBTOTAL\b', r'\bAMOUNT DUE\b', r'\bNET AMOUNT\b',
    r'\bTAX\b', r'\bVAT\b', r'\bDISCOUNT\b', r'\bCASH\b', r'\bVISA\b',
    r'\bINVOICE\b', r'\bRECEIPT\b', r'\bDATE\b', r'\bPHARMACY\b',
    r'\bCUSTOMER\b', r'\bPATIENT\b', r'\bBALANCE\b', r'\bCHANGE\b'
]


def detect_non_medicine_entity(text: str) -> bool:
    """Detects whether text line represents administrative/accounting non-medicine text."""
    clean = text.strip().upper()
    for kw in NON_MEDICINE_KEYWORDS:
        if re.search(kw, clean):
            return True
    return False


# -----------------------------------------------------------------------------
# G5 Mathematical Q_geo Formulation (Frozen Specification Strict Compliance)
# Formula: Q_geo = q_skew * q_sep * q_aspect
# -----------------------------------------------------------------------------

def compute_q_skew(theta_deg: float) -> float:
    """
    Skew penalty factor:
    Penalty starts strictly after 2.0 degrees, reaching 0.0 at 5.0 degrees.
    Formula:
      |theta| <= 2.0: 1.00
      2.0 < |theta| < 5.0: (5.0 - |theta|) / 3.0
      |theta| >= 5.0: 0.00
    """
    theta = abs(float(theta_deg))
    if not math.isfinite(theta):
        return 0.0
    if theta <= 2.0:
        return 1.0
    elif theta >= 5.0:
        return 0.0
    else:
        return float((5.0 - theta) / 3.0)


def compute_q_sep(delta_y_gap: Optional[float], line_h: float) -> float:
    """
    Separation quality factor:
    Normalized gap relative to line height, threshold 0.30 of h_line.
    Strict Rules:
      - Never infer separation from image margins or crop borders!
      - If delta_y_gap is None or non-positive: returns 0.00.
      - Formula:
          ratio = delta_y_gap / line_h
          ratio >= 0.30: 1.00
          0 < ratio < 0.30: ratio / 0.30
    """
    if delta_y_gap is None or line_h <= 0 or not math.isfinite(delta_y_gap) or not math.isfinite(line_h):
        return 0.0
    if delta_y_gap <= 0:
        return 0.0
    ratio = delta_y_gap / line_h
    if ratio >= 0.30:
        return 1.0
    return float(ratio / 0.30)


def evaluate_bounding_boxes_aspect(
    boxes: Optional[List[Dict[str, Any]]],
    crop_w: Optional[int] = None,
    crop_h: Optional[int] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates q_aspect based strictly on OCR bounding boxes quality:
    Strict Remediation Round 5:
      - Valid non-empty boxes list. Absence of boxes -> UNOBSERVED with 0.0 quality.
      - Never infer aspect quality from crop dimensions alone!
      - Box coordinates must be numeric, finite, with width > 0, height > 0 (if y present).
      - Clipping check against image boundaries (0 < x0 and x1 < crop_w).
      - Multi-line grouping: boxes are grouped by line/baseline before checking horizontal overlap.
        Boxes from different lines naturally overlap in x and must NOT be marked overlapping/touching!
    Returns: (q_aspect, metadata_dict)
    """
    if boxes is None or len(boxes) == 0:
        return 0.0, {
            "status": "UNOBSERVED",
            "q_aspect": 0.0,
            "reason": "missing_bounding_boxes",
            "source": "OCR_BOXES"
        }

    valid_parsed: List[Dict[str, Any]] = []
    for i, b in enumerate(boxes):
        if not isinstance(b, dict):
            return 0.0, {
                "status": "DEGENERATE",
                "q_aspect": 0.0,
                "reason": f"invalid_type_box_{i}",
                "source": "OCR_BOXES"
            }
        x0 = b.get("x0")
        x1 = b.get("x1")
        if x0 is None or x1 is None or not (isinstance(x0, (int, float)) and isinstance(x1, (int, float))):
            return 0.0, {
                "status": "DEGENERATE",
                "q_aspect": 0.0,
                "reason": f"invalid_coordinates_box_{i}",
                "source": "OCR_BOXES"
            }
        x0 = float(x0)
        x1 = float(x1)
        if not (math.isfinite(x0) and math.isfinite(x1)):
            return 0.0, {
                "status": "DEGENERATE",
                "q_aspect": 0.0,
                "reason": f"non_finite_coordinates_box_{i}",
                "source": "OCR_BOXES"
            }
        w = x1 - x0
        if w <= 0:
            return 0.0, {
                "status": "DEGENERATE",
                "q_aspect": 0.0,
                "reason": f"zero_or_negative_width_box_{i}",
                "source": "OCR_BOXES"
            }

        y0 = b.get("y0")
        y1 = b.get("y1")
        if y0 is not None and y1 is not None:
            if not (isinstance(y0, (int, float)) and isinstance(y1, (int, float))):
                return 0.0, {
                    "status": "DEGENERATE",
                    "q_aspect": 0.0,
                    "reason": f"non_numeric_y_box_{i}",
                    "source": "OCR_BOXES"
                }
            y0 = float(y0)
            y1 = float(y1)
            if not (math.isfinite(y0) and math.isfinite(y1)) or (y1 - y0) <= 0:
                return 0.0, {
                    "status": "DEGENERATE",
                    "q_aspect": 0.0,
                    "reason": f"zero_or_negative_height_box_{i}",
                    "source": "OCR_BOXES"
                }

        # Check boundary clipping
        if crop_w is not None and crop_w > 0:
            if x0 <= 0 or x1 >= crop_w:
                return 0.0, {
                    "status": "CLIPPED",
                    "q_aspect": 0.0,
                    "reason": f"clipped_at_boundary_box_{i}",
                    "source": "OCR_BOXES"
                }
        if crop_h is not None and crop_h > 0 and y0 is not None and y1 is not None:
            if y0 <= 0 or y1 >= crop_h:
                return 0.0, {
                    "status": "CLIPPED",
                    "q_aspect": 0.0,
                    "reason": f"clipped_at_boundary_box_{i}",
                    "source": "OCR_BOXES"
                }

        valid_parsed.append(dict(b, x0=x0, x1=x1, y0=y0, y1=y1))

    # Multi-line grouping: group boxes by vertical lines if Y coordinates are present
    has_y = all(b.get("y0") is not None and b.get("y1") is not None for b in valid_parsed)
    if has_y and len(valid_parsed) > 1:
        box_heights = [b["y1"] - b["y0"] for b in valid_parsed]
        med_h = float(np.median(box_heights)) if box_heights else 10.0
        by_y = sorted(valid_parsed, key=lambda bx: (bx["y0"] + bx["y1"]) / 2.0)
        lines_list: List[List[Dict[str, Any]]] = []
        for bx in by_y:
            b_center = (bx["y0"] + bx["y1"]) / 2.0
            assigned = False
            for line_boxes in lines_list:
                line_center = float(np.mean([(lb["y0"] + lb["y1"]) / 2.0 for lb in line_boxes]))
                if abs(b_center - line_center) <= 0.50 * max(med_h, 4.0):
                    line_boxes.append(bx)
                    assigned = True
                    break
            if not assigned:
                lines_list.append([bx])
    else:
        lines_list = [valid_parsed]

    # Evaluate overlap and touching strictly WITHIN each line
    for line_idx, line_boxes in enumerate(lines_list):
        sorted_b = sorted(line_boxes, key=lambda b: b["x0"])
        for i in range(len(sorted_b) - 1):
            curr_b = sorted_b[i]
            next_b = sorted_b[i + 1]
            gap = next_b["x0"] - curr_b["x1"]
            if gap < 0:
                return 0.0, {
                    "status": "OVERLAPPING",
                    "q_aspect": 0.0,
                    "reason": f"overlapping_boxes_line_{line_idx}_{i}_{i+1}",
                    "gap": gap,
                    "source": "OCR_BOXES"
                }
            if gap == 0:
                return 0.0, {
                    "status": "TOUCHING",
                    "q_aspect": 0.0,
                    "reason": f"touching_boxes_line_{line_idx}_{i}_{i+1}",
                    "gap": 0.0,
                    "source": "OCR_BOXES"
                }

    return 1.0, {
        "status": "VALID",
        "q_aspect": 1.0,
        "box_count": len(boxes),
        "lines_detected": len(lines_list),
        "source": "OCR_BOXES"
    }


def compute_q_aspect(aspect_valid: bool, degenerate: bool) -> float:
    """Fallback aspect helper for basic checks."""
    if not aspect_valid or degenerate:
        return 0.0
    return 1.0


def compute_q_geo(
    theta_deg: float,
    delta_y_gap: Optional[float],
    line_h: float,
    aspect_valid: bool,
    degenerate: bool
) -> Tuple[float, float, float, float]:
    """
    Frozen Multiplicative Formula: Q_geo = q_skew * q_sep * q_aspect
    Strictly in [0.0, 1.0]. Zero weighted sum.
    Returns: (Q_geo, q_skew, q_sep, q_aspect)
    """
    q_skew = compute_q_skew(theta_deg)
    q_sep = compute_q_sep(delta_y_gap, line_h)
    q_aspect = compute_q_aspect(aspect_valid, degenerate)
    q_geo = float(q_skew * q_sep * q_aspect)
    return q_geo, q_skew, q_sep, q_aspect


def measure_skew_from_pixels(ink_mask: np.ndarray) -> Optional[float]:
    """
    Estimates baseline skew angle in [-5.0, 5.0] degrees directly from 2D pixel ink mask
    by maximizing horizontal projection profile variance.
    Returns None if dimensions or ink are insufficient for measurement.
    """
    h, w = ink_mask.shape
    if h < 4 or w < 8 or np.sum(ink_mask) == 0:
        return None

    angles = np.linspace(-5.0, 5.0, 21)  # step 0.5 deg
    best_angle = 0.0
    best_var = -1.0
    cols = np.arange(w) - (w / 2.0)

    for ang in angles:
        rad = math.radians(ang)
        tan_a = math.tan(rad)
        shifts = np.round(cols * tan_a).astype(int)

        sheared_proj = np.zeros(h, dtype=int)
        for c in range(w):
            s = shifts[c]
            col_vals = ink_mask[:, c]
            if s == 0:
                sheared_proj += col_vals
            elif s > 0:
                sheared_proj[s:] += col_vals[:h - s]
            else:
                sheared_proj[:h + s] += col_vals[-s:]

        v = float(np.var(sheared_proj))
        if v > best_var:
            best_var = v
            best_angle = float(ang)

    return best_angle


def measure_raster_from_crop(
    image_crop: Any,
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[str, Any], GeomObservationState]:
    """
    Extracts physical G5 raster measurements strictly and exclusively from actual 2D image pixels.
    Strict Remediation Round 5:
      - Single text band: inter-line separation cannot be observed -> delta_y_gap is None, q_sep = 0.0,
        and state is GEOM_UNOBSERVED.
      - Margins to crop borders are NEVER treated as separation gaps.
      - q_aspect is evaluated strictly from OCR bounding boxes. Missing boxes -> q_aspect = 0.0,
        aspect status UNOBSERVED, Q_geo = 0.0, and state is GEOM_UNOBSERVED.
      - Never infer q_aspect = 1.0 from crop dimensions alone!
    """
    if image_crop is None:
        return {}, GeomObservationState.GEOM_UNOBSERVED

    if not isinstance(image_crop, np.ndarray) or image_crop.ndim != 2:
        return {"error": "invalid_array_type"}, GeomObservationState.GEOM_UNOBSERVED

    if not np.isfinite(image_crop).all():
        return {
            "error": "non_finite_pixels",
            "q_geo": 0.0, "q_skew": 0.0, "q_sep": 0.0, "q_aspect": 0.0,
            "pixel_extractor_called": True, "source": "IMAGE_PIXELS_2D"
        }, GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    h, w = image_crop.shape
    if h < 4 or w < 4:
        return {
            "error": "degenerate_dimensions", "h": h, "w": w,
            "q_geo": 0.0, "q_skew": 0.0, "q_sep": 0.0, "q_aspect": 0.0,
            "pixel_extractor_called": True, "source": "IMAGE_PIXELS_2D"
        }, GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    # Ink binarization: dark pixels (< 128 for integer, < 0.5 for float)
    if np.issubdtype(image_crop.dtype, np.integer):
        ink = (image_crop < 128)
    else:
        ink = (image_crop < 0.5)

    total_ink = int(np.sum(ink))
    if total_ink == 0 or total_ink == image_crop.size:
        return {
            "error": "all_blank_or_solid_ink",
            "total_ink": total_ink,
            "q_geo": 0.0, "q_skew": 0.0, "q_sep": 0.0, "q_aspect": 0.0,
            "pixel_extractor_called": True,
            "source": "IMAGE_PIXELS_2D"
        }, GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    # Horizontal projection profile
    row_ink = np.sum(ink, axis=1)
    ink_rows = row_ink[row_ink > 0]
    mean_ink = float(np.mean(ink_rows)) if len(ink_rows) > 0 else 0.0
    thresh = 0.15 * mean_ink

    # Detect baseline bands
    bands: List[Tuple[int, int]] = []
    in_band = False
    start_b = 0
    for r, count in enumerate(row_ink):
        if count > thresh:
            if not in_band:
                start_b = r
                in_band = True
        else:
            if in_band:
                bands.append((start_b, r))
                in_band = False
    if in_band:
        bands.append((start_b, h))

    if not bands:
        return {
            "error": "no_baselines_detected",
            "q_geo": 0.0, "q_skew": 0.0, "q_sep": 0.0, "q_aspect": 0.0,
            "pixel_extractor_called": True,
            "source": "IMAGE_PIXELS_2D"
        }, GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    line_h = float(np.mean([e - s for s, e in bands]))
    theta_skew = measure_skew_from_pixels(ink)
    q_skew = compute_q_skew(theta_skew) if theta_skew is not None else 0.0

    # Aspect quality evaluation strictly from OCR bounding boxes
    if bounding_boxes is not None and len(bounding_boxes) > 0:
        q_aspect, aspect_meta = evaluate_bounding_boxes_aspect(bounding_boxes, crop_w=w, crop_h=h)
    else:
        q_aspect = 0.0
        aspect_meta = {
            "status": "UNOBSERVED",
            "q_aspect": 0.0,
            "reason": "missing_bounding_boxes",
            "source": "OCR_BOXES"
        }

    # Inter-line separation evaluation
    if len(bands) < 2:
        # Only 1 text band detected: inter-line separation is unobservable
        measurements = {
            "theta_skew": theta_skew,
            "line_height": line_h,
            "line_gap": None,  # Explicitly unobserved
            "band_count": len(bands),
            "band_coords": bands,
            "gap_coords": [],
            "aspect_valid": (aspect_meta["status"] == "VALID"),
            "aspect_meta": aspect_meta,
            "degenerate": False,
            "q_skew": q_skew,
            "q_sep": 0.0,
            "q_aspect": q_aspect,
            "q_geo": 0.0,
            "pixel_extractor_called": True,
            "source": "IMAGE_PIXELS_2D",
            "observation_detail": "single_line_unobserved_separation"
        }
        return measurements, GeomObservationState.GEOM_UNOBSERVED

    # Multiple physical text lines detected
    gaps = [bands[i + 1][0] - bands[i][1] for i in range(len(bands) - 1)]
    gap_coords = [(bands[i][1], bands[i + 1][0]) for i in range(len(bands) - 1)]
    delta_y = float(min(gaps))

    if delta_y <= 0:
        # Overlapping or degenerate bands
        measurements = {
            "theta_skew": theta_skew,
            "line_height": line_h,
            "line_gap": delta_y,
            "band_count": len(bands),
            "band_coords": bands,
            "gap_coords": gap_coords,
            "aspect_valid": (aspect_meta["status"] == "VALID"),
            "aspect_meta": aspect_meta,
            "degenerate": True,
            "q_skew": q_skew,
            "q_sep": 0.0,
            "q_aspect": 0.0,
            "q_geo": 0.0,
            "pixel_extractor_called": True,
            "source": "IMAGE_PIXELS_2D",
            "observation_detail": "overlapping_or_touching_bands"
        }
        return measurements, GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    q_sep = compute_q_sep(delta_y, line_h)

    # Q_geo = q_skew * q_sep * q_aspect
    if aspect_meta["status"] == "UNOBSERVED" or theta_skew is None:
        q_geo = 0.0
        geom_state = GeomObservationState.GEOM_UNOBSERVED
    else:
        q_geo = float(q_skew * q_sep * q_aspect)
        geom_state = GeomObservationState.GEOM_OBSERVED_VALID if q_geo > 0.0 else GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY

    measurements = {
        "theta_skew": theta_skew,
        "line_height": line_h,
        "line_gap": delta_y,
        "band_count": len(bands),
        "band_coords": bands,
        "gap_coords": gap_coords,
        "aspect_valid": (aspect_meta["status"] == "VALID"),
        "aspect_meta": aspect_meta,
        "degenerate": False,
        "q_skew": q_skew,
        "q_sep": q_sep,
        "q_aspect": q_aspect,
        "q_geo": q_geo,
        "pixel_extractor_called": True,
        "source": "IMAGE_PIXELS_2D"
    }
    return measurements, geom_state


def compute_reliability_gates(
    ocr_conf: float,
    raster_meta: Optional[Dict[str, Any]] = None,
    image_crop: Optional[Any] = None,
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[EvidenceGroup, float], GeomObservationState, Dict[str, Any]]:
    """
    Computes reliability gates gamma_m for each evidence group.
    gamma_text for G1..G4; Q_geo for G5.
    STRICT COMPLIANCE:
      - Ignores ANY 'q_geo' in raster_meta completely.
      - Measures Q_geo strictly from actual 2D pixels in image_crop and OCR boxes.
      - When image_crop is absent or single-line -> GEOM_UNOBSERVED (gamma_5 = 0.0).
      - When image_crop is corrupt/degenerate -> GEOM_OBSERVED_ZERO_QUALITY (gamma_5 = 0.0).
      - When valid multiline with valid boxes -> GEOM_OBSERVED_VALID (gamma_5 = Q_geo > 0.0).
    """
    # 1. Textual OCR Confidence Gate gamma_text
    if ocr_conf >= 0.75:
        gamma_text = 1.00
    elif ocr_conf >= 0.40:
        gamma_text = (ocr_conf - 0.40) / (0.75 - 0.40)
    else:
        gamma_text = 0.00

    gates: Dict[EvidenceGroup, float] = {
        EvidenceGroup.G1_SYNTACTIC: float(gamma_text),
        EvidenceGroup.G2_SPATIAL: float(gamma_text),
        EvidenceGroup.G3_ENVELOPE: float(gamma_text),
        EvidenceGroup.G4_FINANCIAL: float(gamma_text),
        EvidenceGroup.G5_RASTER: 0.00
    }

    # 2. Extract G5 measurements exclusively from image_crop pixels and bounding boxes
    g5_measurements, geom_state = measure_raster_from_crop(image_crop, bounding_boxes=bounding_boxes)

    if geom_state == GeomObservationState.GEOM_OBSERVED_VALID:
        gates[EvidenceGroup.G5_RASTER] = float(g5_measurements.get("q_geo", 0.0))
    else:
        gates[EvidenceGroup.G5_RASTER] = 0.00

    return gates, geom_state, g5_measurements


# -----------------------------------------------------------------------------
# G2 OCR Bounding Box Parsing & Validation (Strict Spatial Layout)
# -----------------------------------------------------------------------------

def validate_and_parse_bounding_boxes(
    raw_boxes: Optional[List[Dict[str, Any]]],
    text_len: int
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Rigorously parses and validates OCR bounding boxes.
    Strict Remediation Round 5:
      1. Coordinate existence, numeric type, finiteness (no NaN, no Inf).
      2. Valid spatial interval: x1 > x0 >= 0.
      3. Mandatory valid text offsets: 0 <= text_start < text_end <= text_len.
         Zero defaulting to 0 strictly prohibited. Missing offsets cause box rejection.
      4. Calculates character scale d_med from actual character widths.
      5. Void spans: evaluated strictly between consecutive boxes on the SAME LINE.
         Never connects boxes across line boundaries!
    """
    metadata: Dict[str, Any] = {
        "status": "UNOBSERVED",
        "valid_box_count": 0,
        "rejected_box_count": 0,
        "rejection_reasons": [],
        "d_med": None,
        "void_spans": []
    }

    if raw_boxes is None or len(raw_boxes) == 0:
        return [], metadata

    valid_boxes = []
    rejected = 0
    rejection_reasons = []

    for i, b in enumerate(raw_boxes):
        if not isinstance(b, dict):
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "NOT_A_DICT"})
            continue
        if "x0" not in b or "x1" not in b:
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "MISSING_X_COORDINATES"})
            continue

        try:
            x0 = float(b["x0"])
            x1 = float(b["x1"])
        except (ValueError, TypeError):
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "NON_NUMERIC_X_COORDINATES"})
            continue

        if not (math.isfinite(x0) and math.isfinite(x1)):
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "NON_FINITE_X_COORDINATES"})
            continue

        if x0 < 0 or x1 <= x0:
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "INVALID_X_INTERVAL", "x0": x0, "x1": x1})
            continue

        # Mandatory text coordinates: must be explicitly present and valid
        if "text_start" not in b or "text_end" not in b:
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "MISSING_TEXT_COORDINATES"})
            continue

        try:
            ts = int(b["text_start"])
            te = int(b["text_end"])
        except (ValueError, TypeError):
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "NON_INTEGER_TEXT_COORDINATES"})
            continue

        if ts < 0 or te <= ts or te > text_len:
            rejected += 1
            rejection_reasons.append({"index": i, "reason": "OUT_OF_BOUNDS_TEXT_COORDINATES", "ts": ts, "te": te, "text_len": text_len})
            continue

        y0 = b.get("y0")
        y1 = b.get("y1")
        if y0 is not None and y1 is not None:
            try:
                y0 = float(y0)
                y1 = float(y1)
                if not (math.isfinite(y0) and math.isfinite(y1)) or y1 <= y0:
                    y0, y1 = None, None
            except (ValueError, TypeError):
                y0, y1 = None, None

        valid_boxes.append(dict(b, x0=x0, x1=x1, y0=y0, y1=y1, text_start=ts, text_end=te))

    metadata["valid_box_count"] = len(valid_boxes)
    metadata["rejected_box_count"] = rejected
    metadata["rejection_reasons"] = rejection_reasons

    if len(valid_boxes) < 2:
        metadata["status"] = "INSUFFICIENT_VALID_BOXES"
        return valid_boxes, metadata

    # Calculate character widths from non-overlapping boxes
    char_widths = []
    for b in valid_boxes:
        txt = b.get("text", "")
        w = b["x1"] - b["x0"]
        if len(txt) > 0 and w > 0:
            char_widths.append(w / len(txt))

    if not char_widths:
        metadata["status"] = "NO_CHARACTER_SCALE"
        return valid_boxes, metadata

    d_med = float(np.median(char_widths))
    metadata["d_med"] = d_med
    gap_thresh = 2.5 * d_med

    # Group boxes by line to avoid creating void_spans across different lines
    has_y = all(b["y0"] is not None and b["y1"] is not None for b in valid_boxes)
    if has_y:
        med_h = float(np.median([b["y1"] - b["y0"] for b in valid_boxes]))
        by_y = sorted(valid_boxes, key=lambda bx: (bx["y0"] + bx["y1"]) / 2.0)
        lines_list: List[List[Dict[str, Any]]] = []
        for bx in by_y:
            b_center = (bx["y0"] + bx["y1"]) / 2.0
            assigned = False
            for line_boxes in lines_list:
                line_center = float(np.mean([(lb["y0"] + lb["y1"]) / 2.0 for lb in line_boxes]))
                if abs(b_center - line_center) <= 0.50 * max(med_h, 4.0):
                    line_boxes.append(bx)
                    assigned = True
                    break
            if not assigned:
                lines_list.append([bx])
    else:
        lines_list = [valid_boxes]

    # Evaluate void_spans strictly within the same line
    for line_boxes in lines_list:
        sorted_line = sorted(line_boxes, key=lambda b: b["x0"])
        for i in range(len(sorted_line) - 1):
            curr_b = sorted_line[i]
            next_b = sorted_line[i + 1]
            gap = next_b["x0"] - curr_b["x1"]
            if gap >= gap_thresh:
                ts = curr_b["text_end"]
                te = next_b["text_start"]
                if te > ts:
                    metadata["void_spans"].append((ts, te))

    metadata["status"] = "OBSERVED_VALID"
    return valid_boxes, metadata


def compute_indentation_offset(
    boxes: Optional[List[Dict[str, Any]]],
    text: str,
    d_med: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes EVID_06: Column Indentation Offset from actual bounding box coordinates.
    Strict Remediation Round 5:
      - Deleted fixed 16.0 threshold: if d_med is missing or invalid, status is strictly UNOBSERVED.
      - Deleted fixed 4.0 line threshold: line grouping uses actual box heights and vertical centers.
      - If boxes lack Y coordinates and no newline exists, lines cannot be determined -> UNOBSERVED.
      - Measures delta_x = x0(line2) - x0(line1).
      - Returns 0.80 if delta_x >= 2.0 * d_med, else 0.0.
    """
    if not boxes or len(boxes) < 2:
        return 0.0, {"status": "UNOBSERVED", "reason": "insufficient_boxes", "source": "OCR_BOXES"}

    if d_med is None or d_med <= 0 or not math.isfinite(d_med):
        return 0.0, {
            "status": "UNOBSERVED",
            "reason": "missing_or_invalid_d_med",
            "source": "OCR_BOXES"
        }

    line1_boxes: List[Dict[str, Any]] = []
    line2_boxes: List[Dict[str, Any]] = []

    if "\n" in text:
        nl = text.find("\n")
        line1_boxes = [b for b in boxes if b.get("text_end") is not None and b["text_end"] <= nl]
        line2_boxes = [b for b in boxes if b.get("text_start") is not None and b["text_start"] > nl]
    else:
        # Check that all boxes have valid numeric Y coordinates
        has_y = all(b.get("y0") is not None and b.get("y1") is not None for b in boxes)
        if not has_y:
            return 0.0, {
                "status": "UNOBSERVED",
                "reason": "missing_y_coordinates_for_line_detection",
                "source": "OCR_BOXES"
            }

        box_heights = [b["y1"] - b["y0"] for b in boxes]
        med_h = float(np.median(box_heights)) if box_heights else 10.0
        by_y = sorted(boxes, key=lambda bx: (bx["y0"] + bx["y1"]) / 2.0)
        lines_list: List[List[Dict[str, Any]]] = []
        for bx in by_y:
            b_center = (bx["y0"] + bx["y1"]) / 2.0
            assigned = False
            for line_boxes in lines_list:
                line_center = float(np.mean([(lb["y0"] + lb["y1"]) / 2.0 for lb in line_boxes]))
                if abs(b_center - line_center) <= 0.50 * max(med_h, 4.0):
                    line_boxes.append(bx)
                    assigned = True
                    break
            if not assigned:
                lines_list.append([bx])

        if len(lines_list) >= 2:
            line1_boxes = lines_list[0]
            line2_boxes = lines_list[1]

    if not line1_boxes or not line2_boxes:
        return 0.0, {"status": "NOT_APPLICABLE", "reason": "single_line_only", "source": "OCR_BOXES"}

    x_ref = min(b["x0"] for b in line1_boxes)
    x_line2 = min(b["x0"] for b in line2_boxes)
    delta_x = x_line2 - x_ref

    thresh = 2.0 * d_med

    if delta_x >= thresh:
        return 0.80, {
            "status": "OBSERVED_INDENTED",
            "delta_x": delta_x,
            "threshold": thresh,
            "x_ref": x_ref,
            "x_line2": x_line2,
            "source": "OCR_BOXES"
        }
    else:
        return 0.0, {
            "status": "OBSERVED_ALIGNED",
            "delta_x": delta_x,
            "threshold": thresh,
            "x_ref": x_ref,
            "x_line2": x_line2,
            "source": "OCR_BOXES"
        }


def extract_evidence_signals(line: InputLine) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Extracts all 13 evidence signals across the 5 independent groups (G1..G5).
    Guarantees:
      - G1 separates signal extraction from delimiter candidate filtering.
      - G2 relies strictly on validated OCR bounding boxes (zero regex fallback, zero magic d_med).
      - G2 computes EVID_06 strictly from box coordinates (zero metadata flag reliance).
      - G5 extracts evidence strictly from 2D image pixels in line.image_crop and OCR boxes.
    """
    text = line.text
    text_len = len(text)
    signals: Dict[str, float] = {}
    details: Dict[str, Any] = {}

    # -------------------------------------------------------------
    # G1: Syntactic / Lexical Separators
    # -------------------------------------------------------------
    slash_in_ratio = bool(re.search(r'\d+\s*/\s*\d+', text))
    has_isolated_slash = bool(re.search(r'(?<!\d)/(?!\d)|\s+/\s+', text))
    raw_slash_matches = list(re.finditer(r'\s*/\s*', text))

    valid_slash_spans = []
    for m in raw_slash_matches:
        s, e = m.span()
        before_char = text[s-1] if s > 0 else ''
        after_char = text[e] if e < len(text) else ''
        if not (before_char.isdigit() and after_char.isdigit()):
            valid_slash_spans.append((s, e))

    if has_isolated_slash:
        signals["EVID_01"] = 1.0
    elif slash_in_ratio:
        signals["EVID_01"] = 0.50
    else:
        signals["EVID_01"] = 0.0
    details["slash_matches"] = valid_slash_spans

    comma_matches = list(re.finditer(r'(?<!\d),\s*|,\s*(?!\d)', text))
    signals["EVID_02"] = 1.0 if comma_matches else 0.0
    details["comma_matches"] = [m.span() for m in comma_matches]

    dash_matches = []
    for m in re.finditer(r'\s+-\s+', text):
        s, e = m.span()
        prefix = text[:s].strip().split()[-1] if text[:s].strip() else ''
        if not re.match(r'^CO$', prefix, re.IGNORECASE):
            dash_matches.append((s, e))

    signals["EVID_03"] = 0.90 if dash_matches else 0.0
    details["dash_matches"] = dash_matches

    plus_matches = list(re.finditer(r'\s*\+\s*|\s+&\s+', text))
    signals["EVID_04"] = 0.80 if plus_matches else 0.0
    details["plus_matches"] = [m.span() for m in plus_matches]

    # -------------------------------------------------------------
    # G2: Spatial Layout via OCR Bounding Boxes
    # -------------------------------------------------------------
    sorted_boxes, box_meta = validate_and_parse_bounding_boxes(line.bounding_boxes, text_len)
    details["g2_meta"] = box_meta
    details["void_spans"] = box_meta.get("void_spans", [])

    signals["EVID_05"] = 1.0 if len(details["void_spans"]) > 0 else 0.0

    d_med = box_meta.get("d_med")
    evid_06, indent_meta = compute_indentation_offset(sorted_boxes, text, d_med=d_med)
    signals["EVID_06"] = evid_06
    details["indent_meta"] = indent_meta

    # -------------------------------------------------------------
    # G3: Structural Dosage Envelope
    # -------------------------------------------------------------
    strength_matches = list(re.finditer(STRENGTH_UNITS, text, re.IGNORECASE))
    signals["EVID_07"] = 1.0 if len(strength_matches) >= 2 else 0.0
    details["strengths"] = [m.group().upper() for m in strength_matches]
    details["strength_spans"] = [m.span() for m in strength_matches]

    form_matches = []
    for pat in DOSAGE_FORMS:
        form_matches.extend(list(re.finditer(pat, text, re.IGNORECASE)))
    signals["EVID_08"] = 1.0 if len(form_matches) >= 2 else 0.0
    details["forms"] = [m.group().upper() for m in form_matches]

    pack_matches = []
    for pat in PACKAGING_PATTERNS:
        pack_matches.extend(list(re.finditer(pat, text, re.IGNORECASE)))
    signals["EVID_09"] = 1.0 if len(pack_matches) >= 2 else 0.0
    details["packs"] = [m.group().upper() for m in pack_matches]

    # -------------------------------------------------------------
    # G4: Financial Multiplicity
    # -------------------------------------------------------------
    price_pat = r'\b\d+\.\d{2}\b(?!\s*(?:MG|G|GM|MCG|ML|IU|%|MG/ML))\b'
    price_matches = list(re.finditer(price_pat, text, re.IGNORECASE))
    signals["EVID_10"] = 1.0 if len(price_matches) >= 2 else 0.0
    details["prices"] = [m.group() for m in price_matches]

    qty_meta = line.raster_metadata.get("quantities", []) if line.raster_metadata else []
    qty_list = list(qty_meta)
    qty_text_matches = list(re.finditer(r'\b(?:QTY|QUANTITY)\s*[:#]?\s*(\d+)\b', text, re.IGNORECASE))
    for qm in qty_text_matches:
        qty_list.append(qm.group(1))

    signals["EVID_11"] = 1.0 if len(qty_list) >= 2 else 0.0
    details["quantities"] = qty_list

    # -------------------------------------------------------------
    # G5: Raster Geometry from Actual 2D Image Pixels
    # -------------------------------------------------------------
    g5_measurements, _ = measure_raster_from_crop(line.image_crop, bounding_boxes=line.bounding_boxes)
    details["g5_measurements"] = g5_measurements

    band_count = g5_measurements.get("band_count", 0)
    delta_y = g5_measurements.get("line_gap")
    line_h = g5_measurements.get("line_height", 0.0)

    if band_count >= 2:
        signals["EVID_12"] = 1.0  # Multiple physical text baselines
        if delta_y is not None and line_h > 0 and (delta_y / line_h) >= 0.30:
            signals["EVID_13"] = 1.0
        else:
            signals["EVID_13"] = 0.0
    else:
        signals["EVID_12"] = 0.0
        signals["EVID_13"] = 0.0

    return signals, details


def compute_conflict_penalties(text: str, n_strengths: int) -> Tuple[float, float, float]:
    """
    Computes P_chem, P_ratio, and total P_conflict.
    Frozen Specification Reference: e1_1_final_closure_amendment.md Section 3.
    """
    # 1. Chemical Conjunction Penalty (P_chem = 0.40)
    has_plus = bool(re.search(r'\b[A-Za-z]+\s*\+\s*[A-Za-z]+', text))
    has_amp = bool(re.search(r'\b[A-Za-z]+\s*&\s*[A-Za-z]+', text))
    p_chem = 0.40 if ((has_plus or has_amp) and n_strengths == 1) else 0.00

    # 2. Fixed-Dose Combination Ratio Penalty (P_ratio = 0.35)
    has_numeric_slash = bool(re.search(r'\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?', text))
    has_numeric_hyphen = bool(re.search(r'\d+(?:\.\d+)?-\d+(?:\.\d+)?', text))
    has_co_prefix = bool(re.search(r'\bCO-[A-Za-z]+', text, re.IGNORECASE))

    p_ratio = 0.35 if (has_numeric_slash or (has_numeric_hyphen and n_strengths <= 1) or (has_co_prefix and has_numeric_slash)) else 0.00

    p_conflict = min(1.0, p_chem + p_ratio)
    return p_chem, p_ratio, p_conflict


def evaluate_structural_envelope(text: str, details: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates whether text line exhibits a cohesive, single-medicine structural envelope (S_env).
    Requires:
      - Exactly 1 dosage strength (n_str == 1)
      - At most 1 dosage form (n_form <= 1)
      - At most 1 packaging count (n_pack <= 1)
      - At most 1 price entry (n_price <= 1)
      - At most 1 quantity entry (n_qty <= 1)
    """
    strengths = details.get("strengths", [])
    forms = details.get("forms", [])
    packs = details.get("packs", [])
    prices = details.get("prices", [])
    quantities = details.get("quantities", [])

    n_str = len(strengths)
    n_form = len(forms)
    n_pack = len(packs)
    n_price = len(prices)
    n_qty = len(quantities)

    is_cohesive = (n_str == 1 and n_form <= 1 and n_pack <= 1 and n_price <= 1 and n_qty <= 1)
    s_env = 1.0 if is_cohesive else 0.0

    inputs = {
        "strength_count": n_str,
        "form_count": n_form,
        "pack_count": n_pack,
        "price_count": n_price,
        "qty_count": n_qty,
        "cohesive": is_cohesive,
        "strengths": strengths,
        "prices": prices,
        "quantities": quantities
    }
    return s_env, inputs
