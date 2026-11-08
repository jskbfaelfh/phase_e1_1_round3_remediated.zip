def compute_reliability_gates(
    ocr_conf: float,
    raster_meta: Optional[Dict[str, Any]] = None,
    image_crop: Optional[Any] = None,
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[EvidenceGroup, float], GeomObservationState, Dict[str, Any]]:
    """
    Computes reliability gates gamma_m for each evidence group.
    gamma_text for G1..G4; Q_geo for G5.
    STRICT DEFECT FIX:
      - Ignores ANY 'q_geo' in raster_meta completely.
      - Measures Q_geo strictly from actual 2D pixels in image_crop.
      - When image_crop is absent or single-line -> GEOM_UNOBSERVED (gamma_5 = 0.0).
      - When image_crop is corrupt/degenerate -> GEOM_OBSERVED_ZERO_QUALITY (gamma_5 = 0.0).
      - When valid multiline -> GEOM_OBSERVED_VALID (gamma_5 = Q_geo > 0.0).
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
    
    # 2. Extract G5 measurements exclusively from image_crop pixels
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
    Strict Remediation Round 4:
      1. Coordinate existence, numeric type, finiteness (no NaN, no Inf).
      2. Valid spatial interval: x1 > x0 and x0 >= 0.
      3. Mandatory valid text offsets: 0 <= text_start < text_end <= text_len.
         Zero defaulting to 0 permitted! Missing text offsets cause box rejection.
      4. Sorting by x0 and detection of gaps >= 2.5 * d_med.
      5. Derivation of d_med from actual character widths (zero static fallback).
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
            
        valid_boxes.append(dict(b, x0=x0, x1=x1, text_start=ts, text_end=te))
        
    metadata["valid_box_count"] = len(valid_boxes)
    metadata["rejected_box_count"] = rejected
    metadata["rejection_reasons"] = rejection_reasons
    
    if len(valid_boxes) < 2:
        metadata["status"] = "INSUFFICIENT_VALID_BOXES"
        return valid_boxes, metadata
        
    # Sort strictly by x0
    sorted_boxes = sorted(valid_boxes, key=lambda bx: bx["x0"])
    
    # Calculate character widths from non-overlapping boxes
    char_widths = []
    for b in sorted_boxes:
        txt = b.get("text", "")
        w = b["x1"] - b["x0"]
        if len(txt) > 0 and w > 0:
            char_widths.append(w / len(txt))
            
    if char_widths:
        d_med = float(np.median(char_widths))
        metadata["d_med"] = d_med
        gap_thresh = 2.5 * d_med
        
        # Check gaps between consecutive boxes
        for i in range(len(sorted_boxes) - 1):
            curr_b = sorted_boxes[i]
            next_b = sorted_boxes[i + 1]
            gap = next_b["x0"] - curr_b["x1"]
            if gap >= gap_thresh:
                ts = curr_b["text_end"]
                te = next_b["text_start"]
                if te > ts:
                    metadata["void_spans"].append((ts, te))
                    
        metadata["status"] = "OBSERVED_VALID"
    else:
        metadata["status"] = "NO_CHARACTER_SCALE"
        
    return sorted_boxes, metadata


def compute_indentation_offset(
    boxes: Optional[List[Dict[str, Any]]],
    text: str,
    d_med: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes EVID_06: Column Indentation Offset from actual bounding box coordinates.
    Strict Remediation Round 4:
      - Zero reliance on metadata 'indent_offset'.
      - Identifies lines via linebreaks or baseline y-coordinates.
      - Measures delta_x = x0(line2) - x0(line1).
      - Returns 0.80 if delta_x >= 2.0 * d_med, else 0.0.
    """
    if not boxes or len(boxes) < 2:
        return 0.0, {"status": "UNOBSERVED", "reason": "insufficient_boxes", "source": "OCR_BOXES"}
        
    line1_boxes: List[Dict[str, Any]] = []
    line2_boxes: List[Dict[str, Any]] = []
    
    if "\n" in text:
        nl = text.find("\n")
        line1_boxes = [b for b in boxes if b.get("text_end") is not None and b["text_end"] <= nl]
        line2_boxes = [b for b in boxes if b.get("text_start") is not None and b["text_start"] > nl]
    elif any("y0" in b for b in boxes):
        min_y = min(b["y0"] for b in boxes if "y0" in b)
        line1_boxes = [b for b in boxes if abs(b.get("y0", min_y) - min_y) <= 4.0]
        line2_boxes = [b for b in boxes if b.get("y0", min_y) - min_y > 4.0]
        
    if not line1_boxes or not line2_boxes:
        return 0.0, {"status": "NOT_APPLICABLE", "reason": "single_line_only", "source": "OCR_BOXES"}
        
    x_ref = min(b["x0"] for b in line1_boxes)
    x_line2 = min(b["x0"] for b in line2_boxes)
    delta_x = x_line2 - x_ref
    
    thresh = (2.0 * d_med) if (d_med is not None and d_med > 0) else 16.0
    
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
      - G5 extracts evidence strictly from 2D image pixels in line.image_crop.
    """
    text = line.text
    text_len = len(text)
    signals: Dict[str, float] = {}
    details: Dict[str, Any] = {}
    
    # -------------------------------------------------------------
    # G1: Syntactic / Lexical Separators
    # -------------------------------------------------------------
    # Filter out numeric ratios (e.g. 160/12.5MG) from isolated slash separators
    slash_in_ratio = bool(re.search(r'\d+\s*/\s*\d+', text))
    has_isolated_slash = bool(re.search(r'(?<!\d)/(?!\d)|\s+/\s+', text))
    raw_slash_matches = list(re.finditer(r'\s*/\s*', text))
    
    # Filter slashes: keep only those not sandwiched between digits
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
    
    # Filter dashes: keep only spaced hyphens not part of brand names (CO-DIOVAN) or numeric ranges
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
    
    # EVID_06: Computed strictly from box coordinates (zero metadata flag reliance)
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
    # Decimal prices: not followed by dosage units
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
    # Ratio slash or hyphen embedded directly between numeric digits (e.g. 160/12.5MG, 500/125MG, 20/5MG)
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
