# Phase E1.1 Isolated Implementation Traceability Matrix
## Direct Code Mapping of Frozen Mathematical Specifications and State Rules

**Document Status:** FROZEN IMPLEMENTATION TRACEABILITY MATRIX (REMEDIATION ROUND 4)  
**Implementation Root:** `ai-service/experiments/phase3_prototype_1_7/phase_e1_1_isolated_engine/`  
**Specification References:**
- `e1_1_final_closure_amendment.md`
- `e1_1_evidence_independence_audit.md`
- `e1_1_decision_consistency_correction.md`
- `e1_1_output_compatibility_matrix.md`
- `e1_1_matching_algorithm_and_metrics.md`

---

## 1. Core Mathematical Equations & Weights Mapping

$$\begin{array}{|l|l|l|l|}
\hline
\mathbf{Mathematical Specification} & \mathbf{Formula / Parameter} & \mathbf{Source File} & \mathbf{Function / Class / Line Range} \\ \hline
\text{Base Group Weights } w_m & (w_1=0.30, w_2=0.25, w_3=0.20, w_4=0.15, w_5=0.10) & \text{engine/decision\_engine.py} & \text{BASE\_WEIGHTS (Lines 21–27)} \\ \hline
\text{Text Reliability Gate } \Gamma_{\text{text}} & \Gamma_{\text{text}}(\bar{C}_{\text{ocr}}) \in \{1.0, \text{linear}, 0.0\} & \text{engine/extractors.py} & \text{compute\_reliability\_gates (Lines 284–290)} \\ \hline
\text{Geometric Reliability } Q_{\text{geo}} & q_{\text{skew}} \cdot q_{\text{sep}} \cdot q_{\text{aspect}} & \text{engine/extractors.py} & \text{compute\_q\_geo (Lines 118–125)} \\ \hline
\text{Active Measurement Capacity } W_{\text{active}} & \sum_{m=1}^5 w_m \cdot \gamma_m & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 328–341)} \\ \hline
\text{Capacity Floor Threshold } \tau_{\text{floor}} & \tau_{\text{active\_floor}} = 0.30 & \text{engine/decision\_engine.py} & \text{TAU\_ACTIVE\_FLOOR (Line 30)} \\ \hline
\text{Intra-Group Bounded Saturation } S_m & S_m = \max_{j \in G_m}(e_j) & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 305–317)} \\ \hline
\text{Master Normalized Score } S_{\text{norm}} & E_{\text{mass}} / W_{\text{active}} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 360–366)} \\ \hline
\text{Conflict Penalty } P_{\text{conflict}} & \min(1.0, P_{\text{chem}} + P_{\text{ratio}}) & \text{engine/extractors.py} & \text{compute\_conflict\_penalties (Lines 529–548)} \\ \hline
\text{Master Heuristic Risk Score } \text{HRS} & \max(0.0, S_{\text{norm}} - P_{\text{conflict}}) & \text{engine/decision\_engine.py} & \text{analyze\_line (Line 362)} \\ \hline
\end{array}$$

---

## 2. Evidence Extractors & Signal Definitions (EVID_01 to EVID_13)

$$\begin{array}{|c|l|l|l|l|}
\hline
\mathbf{Group} & \mathbf{Signal ID} & \mathbf{Target Phenomenon} & \mathbf{Implementation File} & \mathbf{Code Function / Regex Matcher} \\ \hline
\multirow{4}{*}{\mathbf{G_1}} & \text{EVID\_01} & \text{Slash Delimiter } (`/`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 436–447)} \\
& \text{EVID\_02} & \text{Comma Delimiter } (`,`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 448–451)} \\
& \text{EVID\_03} & \text{Spaced Dash } (` - `) & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 452–455)} \\
& \text{EVID\_04} & \text{Conjunction } (`+`, `\&`) & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 456–459)} \\ \hline
\multirow{2}{*}{\mathbf{G_2}} & \text{EVID\_05} & \text{Whitespace Void Gap } (\ge 2.5 d_{\text{med}}) & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 461–468)} \\
& \text{EVID\_06} & \text{Column Indentation Offset} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 469–473)} \\ \hline
\multirow{3}{*}{\mathbf{G_3}} & \text{EVID\_07} & \text{Repeated Dosage Strengths} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 477–481)} \\
& \text{EVID\_08} & \text{Repeated Dosage Forms} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 482–487)} \\
& \text{EVID\_09} & \text{Repeated Packaging Counts} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 488–493)} \\ \hline
\multirow{2}{*}{\mathbf{G_4}} & \text{EVID\_10} & \text{Multiple Price Patterns} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 497–500)} \\
& \text{EVID\_11} & \text{Multiple Item Quantities} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 501–504)} \\ \hline
\multirow{2}{*}{\mathbf{G_5}} & \text{EVID\_12} & \text{Vertical Sub-line Baselines (Pixel)} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 508–517)} \\
& \text{EVID\_13} & \text{Inter-line Blank Pixel Valley (Pixel)} & \text{engine/extractors.py} & \text{extract\_evidence\_signals (Lines 518–523)} \\ \hline
\end{array}$$

---

## 3. Hierarchical Gate Precedence Implementation

$$\begin{array}{|l|l|l|l|}
\hline
\mathbf{Execution Step} & \mathbf{Evaluated Precedence Condition} & \mathbf{Implementation File} & \mathbf{Code Block / Method} \\ \hline
\mathbf{Step 1: Entity Type Gate} & \text{detect\_non\_medicine\_entity(text) } \implies \text{NON\_APPLICABLE} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 266–294)} \\ \hline
\mathbf{Step 2: Capacity Noise Gate} & W_{\text{active}} < 0.30 \implies \text{ABSTAIN\_COUNT} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 374–402)} \\ \hline
\mathbf{Step 3: Active Conflict Gate} & (\sum S_m \gamma_m > 0) \land P_{\text{conflict}} > 0 \implies \text{PROVISIONAL} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 407–436)} \\ \hline
\mathbf{Step 4: Definitive Multi Gate} & \text{HRS} \ge 0.70 \land N_{\text{multi}} \ge 2 \implies \text{MULTIPLE\_MEDICINES} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 442–473)} \\ \hline
\mathbf{Step 5: Definitive Single Gate} & \text{HRS} < 0.30 \land S_{\text{env}} == 1 \land \sum S_m \gamma_m == 0 \land P == 0 & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 479–510)} \\ \hline
\mathbf{Step 6: Residual Provisional} & \text{Delegated state with physical boundary support} & \text{engine/decision\_engine.py} & \text{analyze\_line (Lines 515–566)} \\ \hline
\end{array}$$

---

## 4. Output State Compatibility Matrix & Axiom Validator

- **Implementation:** `validate_output_compatibility(output: DecisionOutput)` in `engine/decision_engine.py` (Lines 47–62).
- **Enforced States:** 10 canonical valid states in `CANONICAL_VALID_STATES` (Lines 33–44).
- **Prohibited States:** Hard runtime validation exception raised if any combination violates the 7 forbidden axioms.

---

## 5. Hungarian Partial Matching Optimization & Boundary Precision

- **Implementation:** `optimal_hungarian_matching` in `engine/matching.py` (Lines 35–104).
- **Augmented Size:** $(m+n) \times (m+n)$ square matrix with 4 functional blocks:
  1. $C_{\mathcal{P}, \mathcal{G}}$: primary matches with $-(M^* + \text{IoU})$.
  2. $C_{\mathcal{P}, \text{slack}}$: private diagonal dummy columns for unmatched predictions at cost $0.0$.
  3. $C_{\text{slack}, \mathcal{G}}$: private diagonal dummy rows for unmatched ground truth at cost $0.0$.
  4. $C_{\text{slack}, \text{slack}}$: zero cost block for leftover slack balancing.
- **Cardinality Bound:** $M^* = \min(m, n) + 1.0$.
- **Boundary IoU Rule:** Strict unrounded comparison ($0.89996 < 0.90$ rejected, $0.90000 \ge 0.90$ accepted).

---

## 6. Provenance & Geometry Observation Semantics (Round 4)

- **Implementation:** `GeomObservationState` in `engine/types.py` and `compute_reliability_gates`, `measure_raster_from_crop` in `engine/extractors.py`.
- **Exact States:**
  - `GEOM_OBSERVED_VALID`: 2D pixel crop present and analyzed, $\ge 2$ physical text bands detected with valid separation gap, $Q_{\text{geo}} > 0$.
  - `GEOM_OBSERVED_ZERO_QUALITY`: 2D pixel crop present and analyzed, but degraded (no ink, skew $\ge 5.0^\circ$, or degenerate dimensions).
  - `GEOM_UNOBSERVED`: `image_crop` is None, OR single-line text crop where inter-line separation cannot be physically observed. Metadata `q_geo` 100% ignored.
- **Bounding Box Aspect & Indentation:**
  - `evaluate_bounding_boxes_aspect`: evaluated on actual OCR boxes (checking valid, touching, clipped, overlapping, degenerate, and unobserved).
  - `compute_indentation_offset`: measures $\Delta x = x_0^{(\text{line2})} - x_0^{(\text{line1})}$ directly from box coordinates relative to $d_{\text{med}}$, zero metadata reliance.
- **Constituent Tracking:**
  - `find_boundary_delimiters`: when merging overlapping intervals, constituent records and sources are retained in `constituents` array for independent auditability.
