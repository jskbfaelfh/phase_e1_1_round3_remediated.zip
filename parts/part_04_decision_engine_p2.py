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
