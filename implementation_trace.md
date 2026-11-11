# Phase E1.1 Isolated Implementation Traceability Matrix
## Direct Code Mapping of Frozen Mathematical Specifications and State Rules

**Document Status:** FROZEN IMPLEMENTATION TRACEABILITY MATRIX (REMEDIATION ROUND 5)  
**Implementation Root:** `ai-service/experiments/phase3_prototype_1_7/phase_e1_1_isolated_engine/`  
**Specification References:**
- `e1_1_final_closure_amendment.md`
- `e1_1_decision_output_state_matrix.md`
- `e1_1_evidence_independence_audit.md`
- `e1_1_decision_consistency_correction.md`
- `e1_1_matching_algorithm_and_metrics.md`

---

## 1. Core Mathematical Equations & Weights Mapping

$$\begin{array}{|l|l|l|l|}
\hline
\mathbf{Mathematical Specification} & \mathbf{Formula / Parameter} & \mathbf{Source File} & \mathbf{Function / Class / Line Range} \\ \hline
\text{Base Group Weights } w_m & (w_1=0.30, w_2=0.25, w_3=0.20, w_4=0.15, w_5=0.10) & \text{engine/decision\_engine.py} & \text{BASE\_WEIGHTS} \\ \hline
\text{Text Reliability Gate } \Gamma_{\text{text}} & \Gamma_{\text{text}}(\bar{C}_{\text{ocr}}) \in \{1.0, \text{linear}, 0.0\} & \text{engine/extractors.py} & \text{compute\_reliability\_gates} \\ \hline
\text{Geometric Reliability } Q_{\text{geo}} & q_{\text{skew}} \cdot q_{\text{sep}} \cdot q_{\text{aspect}} & \text{engine/extractors.py} & \text{compute\_q\_geo} \\ \hline
\text{Active Measurement Capacity } W_{\text{active}} & \sum_{m=1}^5 w_m \cdot \gamma_m & \text{engine/decision\_engine.py} & \text{analyze\_line} \\ \hline
\text{Capacity Floor Threshold } \tau_{\text{floor}} & \tau_{\text{active\_floor}} = 0.30 & \text{engine/decision\_engine.py} & \text{TAU\_ACTIVE\_FLOOR} \\ \hline
\text{Intra-Group Bounded Saturation } S_m & S_m = \max_{j \in G_m}(e_j) & \text{engine/decision\_engine.py} & \text{analyze\_line} \\ \hline
\text{Master Normalized Score } S_{\text{norm}} & E_{\text{mass}} / W_{\text{active}} & \text{engine/decision\_engine.py} & \text{analyze\_line} \\ \hline
\text{Conflict Penalty } P_{\text{conflict}} & \min(1.0, P_{\text{chem}} + P_{\text{ratio}}) & \text{engine/extractors.py} & \text{compute\_conflict\_penalties} \\ \hline
\text{Master Heuristic Risk Score } \text{HRS} & \max(0.0, S_{\text{norm}} - P_{\text{conflict}}) & \text{engine/decision\_engine.py} & \text{analyze\_line} \\ \hline
\end{array}$$

---

## 2. Evidence Extractors & Signal Definitions (EVID_01 to EVID_13)

$$\begin{array}{|c|l|l|l|l|}
\hline
\mathbf{Group} & \mathbf{Signal ID} & \mathbf{Target Phenomenon} & \mathbf{Implementation File} & \mathbf{Code Function / Implementation} \\ \hline
\multirow{4}{*}{\mathbf{G_1}} & \text{EVID\_01} & \text{Slash Delimiter } (`/`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_02} & \text{Comma Delimiter } (`,`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_03} & \text{Spaced Dash } (` - `) & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_04} & \text{Conjunction } (`+`, `\&`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\ \hline
\multirow{2}{*}{\mathbf{G_2}} & \text{EVID\_05} & \text{Whitespace Void Gap } (\ge 2.5 d_{\text{med}}) & \text{engine/extractors.py} & \text{validate\_and\_parse\_bounding\_boxes} \\
& \text{EVID\_06} & \text{Column Indentation Offset} & \text{engine/extractors.py} & \text{compute\_indentation\_offset} \\ \hline
\multirow{3}{*}{\mathbf{G_3}} & \text{EVID\_07} & \text{Repeated Dosage Strengths} & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_08} & \text{Repeated Dosage Forms} & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_09} & \text{Repeated Packaging Counts} & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\ \hline
\multirow{2}{*}{\mathbf{G_4}} & \text{EVID\_10} & \text{Multiple Price Patterns} & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\
& \text{EVID\_11} & \text{Multiple Item Quantities} & \text{engine/extractors.py} & \text{extract\_evidence\_signals} \\ \hline
\multirow{2}{*}{\mathbf{G_5}} & \text{EVID\_12} & \text{Vertical Sub-line Baselines (Pixel)} & \text{engine/extractors.py} & \text{measure\_raster\_from\_crop} \\
& \text{EVID\_13} & \text{Inter-line Blank Pixel Valley (Pixel)} & \text{engine/extractors.py} & \text{measure\_raster\_from_crop} \\ \hline
\end{array}$$

---

## 3. Hierarchical Gate Precedence Implementation

$$\begin{array}{|l|l|l|l|}
\hline
\mathbf{Execution Step} & \mathbf{Evaluated Precedence Condition} & \mathbf{Implementation File} & \mathbf{Code Block / Method} \\ \hline
\mathbf{Step 1: Entity Type Gate} & \text{detect\_non\_medicine\_entity(text) } \implies \text{NON\_APPLICABLE} & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 1)} \\ \hline
\mathbf{Step 2: Capacity Noise Floor} & W_{\text{active}} < 0.30 \implies \text{ABSTAIN\_COUNT} & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 2)} \\ \hline
\mathbf{Step 3: Active Conflict Gate} & \sum(S_m \cdot \gamma_m) > 0 \land P_{\text{conflict}} > 0 \implies \text{PROVISIONAL} & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 3)} \\ \hline
\mathbf{Step 4: Definitive Multiplicity} & \text{HRS} \ge 0.70 \land N_{\text{multi}} \ge 2 & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 4)} \\ \hline
\mathbf{Step 5: Definitive Singleness} & \text{HRS} < 0.30 \land S_{\text{env}} = 1 \land \text{All } S_m = 0 & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 5)} \\ \hline
\mathbf{Step 6: Residual Provisional} & \text{Default fallback when gates unreached} & \text{engine/decision\_engine.py} & \text{analyze\_line (Step 6)} \\ \hline
\end{array}$$

---

## 4. Remediation Round 5 Specific Defect Traceability

1. **Definitive Multiplicity with Missing Boundaries:**
   - *Requirement:* Never declare `DISENTANGLED_BOUNDARY` or emit 1 entity when `MULTIPLE_MEDICINES` is decided without verified boundary cuts.
   - *Fix:* `engine/decision_engine.py` Step 4 branches on `boundary_delims` and `len(candidate_spans) >= 2`. When cuts are unsupported, emits `ABSTAIN_UNSUPPORTED_BOUNDARY` with 0 spans.
   - *Verification:* `test_remediation_regression.py` (`REG_08`, `REG_09`).

2. **$q_{\text{aspect}}$ from Image Crop Dimensions:**
   - *Requirement:* Missing bounding boxes must never be awarded $q_{\text{aspect}} = 1.0$ from crop dimensions alone. Must evaluate strictly as `UNOBSERVED` with 0.0 quality.
   - *Fix:* `engine/extractors.py` (`evaluate_bounding_boxes_aspect`, `measure_raster_from_crop`).
   - *Verification:* `test_remediation_regression.py` (`REG_01`, `REG_06`).

3. **Multi-Line Bounding Box Horizontal Overlap:**
   - *Requirement:* Boxes on different lines naturally share horizontal intervals; they must not be marked touching/overlapping.
   - *Fix:* `engine/extractors.py` (`evaluate_bounding_boxes_aspect` groups boxes by line before checking horizontal gaps).
   - *Verification:* `test_remediation_regression.py` (`REG_03`).

4. **Indentation Offset Fixed Fallbacks (16.0 and 4.0):**
   - *Requirement:* Remove static thresholds 16.0 and 4.0 from indentation offset calculation.
   - *Fix:* `engine/extractors.py` (`compute_indentation_offset` requires valid $d_{\text{med}}$ and dynamic line height thresholds, else returns `UNOBSERVED`).
   - *Verification:* `test_remediation_regression.py` (`REG_02`, `REG_04`).
