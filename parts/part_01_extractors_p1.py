"""
Stage E1.1 Disentanglement Decision Engine - Feature & Evidence Signal Extractors
Frozen Specification Reference: e1_1_final_closure_amendment.md
Evidence Groups:
  G1: Syntactic / Lexical Separators (EVID_01..EVID_04)
  G2: Spatial Layout via OCR Bounding Boxes (EVID_05, EVID_06)
  G3: Structural Dosage Envelope (EVID_07..EVID_09)
  G4: Financial Multiplicity (EVID_10, EVID_11)
  G5: Raster Geometry from Actual Image Pixels (EVID_12, EVID_13)
Remediation Round 4
"""

import math
import re
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .types import EvidenceGroup, GeomObservationState, InputLine


# Standard Dosage Units Regex
STRENGTH_UNITS = r'\d+(?:\.\d+)?\s*(?:MG|G|GM|MCG|ML|IU|%|MG/ML)(?=[A-Z]|$|[^A-Za-z0-9])'

# Standard Dosage Form Patterns
DOSAGE_FORMS = [
    r'\bTAB(?:LETS?)?\b', r'\bCAP(?:SULES?)?\b', r'\bSYR(?:UP)?\b',
    r'\bAMP(?:OULES?)?\b', r'\bVIAL\b', r'\bSUSP(?:ENSION)?\b',
    r'\bCREAM\b', r'\bOINT(?:MENT)?\b', r'\bDROPS?\b', r'\bSOL(?:UTION)?\b',
    r'\bINJ(?:ECTION)?\b', r'\bSUPP(?:OSITORY)?\b', r'\bSACHET\b'
]

# Standard Packaging Form Patterns
PACKAGING_PATTERNS = [
    r'\b\d+\s*X\s*\d+\b', r'\b\d+\s*STRIPS?\b', r'\b\d+\s*TABS?\b',
    r'\bBOTTLE\b', r'\bPACK\b', r'\bBOX\b', r'\bBLISTER\b'
]

# Accounting / Administrative Non-Medicine Keywords
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
    Strict Remediation Round 4:
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
    Evaluates q_aspect based on OCR bounding boxes quality:
    Strict Remediation Round 4:
      - Valid non-empty boxes list.
      - Box dimensions: width > 0, height > 0 (if present).
      - Zero overlap between distinct boxes.
      - Non-touching / non-fused (gap > 0 between consecutive boxes).
      - Not clipped against image boundaries (if crop dimensions known: 0 < x0 and x1 < crop_w).
    Returns: (q_aspect, metadata_dict)
    """
    if boxes is None or len(boxes) == 0:
        return 0.0, {
            "status": "UNOBSERVED",
            "q_aspect": 0.0,
            "reason": "missing_bounding_boxes",
            "source": "OCR_BOXES"
        }
        
    for i, b in enumerate(boxes):
        x0 = b.get("x0")
        x1 = b.get("x1")
        if x0 is None or x1 is None or not (math.isfinite(x0) and math.isfinite(x1)):
            return 0.0, {
                "status": "DEGENERATE",
                "q_aspect": 0.0,
                "reason": f"invalid_coordinates_box_{i}",
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

    # Sort boxes by x0 to check touching and overlapping
    sorted_b = sorted(boxes, key=lambda b: b["x0"])
    for i in range(len(sorted_b) - 1):
        curr_b = sorted_b[i]
        next_b = sorted_b[i + 1]
        gap = next_b["x0"] - curr_b["x1"]
        if gap < 0:
            return 0.0, {
                "status": "OVERLAPPING",
                "q_aspect": 0.0,
                "reason": f"overlapping_boxes_{i}_{i+1}",
                "gap": gap,
                "source": "OCR_BOXES"
            }
        if gap == 0:
            return 0.0, {
                "status": "TOUCHING",
                "q_aspect": 0.0,
                "reason": f"touching_boxes_{i}_{i+1}",
                "gap": 0.0,
                "source": "OCR_BOXES"
            }
            
    return 1.0, {
        "status": "VALID",
        "q_aspect": 1.0,
        "box_count": len(boxes),
        "source": "OCR_BOXES"
    }


def compute_q_aspect(aspect_valid: bool, degenerate: bool) -> float:
    """Fallback aspect helper for basic crop dimension checks."""
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


def measure_skew_from_pixels(ink_mask: np.ndarray) -> float:
    """
    Estimates baseline skew angle in [-5.0, 5.0] degrees directly from 2D pixel ink mask
    by maximizing horizontal projection profile variance.
    """
    h, w = ink_mask.shape
    if h < 4 or w < 8 or np.sum(ink_mask) == 0:
        return 0.0
        
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
    Strict Remediation Round 4:
      - When only 1 text band is detected, delta_y_gap is None and q_sep is 0.0.
      - Margins to crop borders are NEVER treated as separation gaps.
      - Separation observation state is GEOM_UNOBSERVED when inter-line measurement is not possible.
      - Evaluates q_aspect with box clipping, overlap, and touching checks.
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
    q_skew = compute_q_skew(theta_skew)
    
    # Aspect quality evaluation
    crop_dim_valid = bool(w >= 8 and h >= 8)
    if bounding_boxes is not None and len(bounding_boxes) > 0:
        q_aspect, aspect_meta = evaluate_bounding_boxes_aspect(bounding_boxes, crop_w=w, crop_h=h)
    else:
        q_aspect = 1.0 if crop_dim_valid else 0.0
        aspect_meta = {"status": "VALID_CROP_ONLY", "q_aspect": q_aspect}
        
    # STRICT REMEDIATION ROUND 4: Never use crop margins as separation gap!
    if len(bands) < 2:
        # Only 1 text band detected: inter-line separation cannot be observed
        measurements = {
            "theta_skew": theta_skew,
            "line_height": line_h,
            "line_gap": None,  # Explicitly unobserved
            "band_count": len(bands),
            "band_coords": bands,
            "gap_coords": [],
            "aspect_valid": crop_dim_valid,
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
            "aspect_valid": crop_dim_valid,
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
    q_geo = float(q_skew * q_sep * q_aspect)
    geom_state = GeomObservationState.GEOM_OBSERVED_VALID if q_geo > 0.0 else GeomObservationState.GEOM_OBSERVED_ZERO_QUALITY
    
    measurements = {
        "theta_skew": theta_skew,
        "line_height": line_h,
        "line_gap": delta_y,
        "band_count": len(bands),
        "band_coords": bands,
        "gap_coords": gap_coords,
        "aspect_valid": crop_dim_valid,
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


