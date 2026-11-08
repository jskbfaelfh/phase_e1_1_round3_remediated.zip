# Part 10: Implementation Trace, Checksums, and Execution Reports

## 1. SHA256SUMS.txt
```
8cb341c87ef58abaf27875b29da650b6bf61b7e13232592fc91e7e409289e355  README.md
60858a202a76a6a918b1f6d62e0203105b95e6527aaea1488fdfcbfe00bad58f  implementation_trace.md
9342d1953f605489c5084ddde18aa0acb83238c3d2f29bffb116dde3e2f920b9  run_all.py
32f28956dfe71c5684febcb5d777ce40ec68159c91a179ce8f8da9fc9e176db7  engine/__init__.py
cea7b95548e4ca29075023fa15ecc1f006f6129836792ec2bd4105b3f8ad0aec  engine/decision_engine.py
fad1e39ab1e96535f4be1fe1514830a7892b0c20e29e6102bd81a214415e9138  engine/extractors.py
d04786f7a3b5f224ca8137a4879a2e47ea8437500ec7631b7f2f040114c01fc6  engine/matching.py
47885a2225b7900d62ae12e5706ccc36d24ff8543e9f25d8a61177f151a0e8c7  engine/types.py
c97e33763714ce9ab2b09a1a3d85100ed2b6742417252e475176b0c9b91086d9  reports/e1_1_implementation_and_test_report.md
2cd72c02168920c2f25bdbbcbbd5c10645d1fd6d0988906873567e40b7dc94a9  reports/remediation_report.md
022f65219422392809f55c5b403d201e8afa9626488fa56f5c6459b2c844dd3c  synthetic_cases/__init__.py
b490877d8b11a38475d418f92caceb25ef67979e5e99ea1a4d35b5151b88cd0b  synthetic_cases/cases.py
5ed89cc5514adc0f863ced7a3154ff02b702dff4811d4e6cfc308a2a66515ef9  tests/test_hungarian_matching.py
48a29119bd5c844fb1404a7fcb0d9faff2b0bb76f1ab1814e509c2671f4e7f0d  tests/test_remediation_regression.py
6e9cfa7dbcbdc24680674fe4e28f0f7e0faa4f9632c57b4675bfc9c47a9d5f97  tests/test_safety_invariants.py
3c77f2e6f83ee378baca9e1e7a6d42d2c1f6ce8dedddd657cb06b3d1c489dbf5  tests/test_synthetic_suite.py

```

## 2. Implementation Trace

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


## 3. Remediation Report

# Phase E1.1 Engineering Remediation Report — Round 4
**Date:** `2026-11-08T16:49:10.475371`  
**Status:** `ROUND_4_REMEDIATION_IMPLEMENTED — INDEPENDENT_REAUDIT_REQUIRED`  

---

## 1. Summary of Defect Remediations and Independent Proofs (Round 4)

| Audit Item | Remediated Defect | Implementation File & Line | Regression Verification Test | Status |
|:---|:---|:---|:---|:---:|
| **G5 Separation Gap** | Strict rule: delta_y_gap measured ONLY between >= 2 physical text bands. Zero use of image margins or crop borders. Single-line crop -> GEOM_UNOBSERVED. | `engine/extractors.py` | `REG_05`, Invariant `INV_06` | **VERIFIED** |
| **q_aspect OCR Boxes** | Separated crop dimensions from OCR bounding boxes. Evaluates valid, touching, clipped, overlapping, zero-dimension, and unobserved boxes. | `engine/extractors.py` | `REG_06` | **VERIFIED** |
| **G2 EVID_06 Indentation** | Derived horizontal indentation Delta x strictly from physical bounding box coordinates ($x_0(\text{line2}) - x_0(\text{line1})$). Zero reliance on metadata. | `engine/extractors.py` | `REG_08` | **VERIFIED** |
| **Delimiter Extraction** | Protected brand names with comma, chemical formulas with '+', compound brands with hyphen (`CO-DIOVAN`), numerical ranges (`1-2`), and ratios (`160/12.5MG`). | `engine/extractors.py`, `engine/decision_engine.py` | `REG_09` | **VERIFIED** |
| **Constituent Tracking** | When overlapping delimiters are merged, all constituent records and sources are retained in a dedicated `constituents` array for auditing. | `engine/decision_engine.py` | `REG_09` | **VERIFIED** |
| **OCR Text Coordinates** | Strict validation of `text_start` and `text_end`: mandatory presence, integer type, positive interval, within text bounds. Zero defaulting to 0 strictly enforced. | `engine/extractors.py` | `REG_07` | **VERIFIED** |
| **Character Integrity** | Non-vacuous bitwise reversibility with negative mutation test (modifying 1 character strictly fails reversibility check). | `engine/matching.py`, `tests/test_remediation_regression.py` | `REG_10`, Invariant `INV_05` | **VERIFIED** |
| **Structural Envelope** | Added financial price bounds ($N_{\text{price}} \le 1$) and quantity bounds ($N_{\text{qty}} \le 1$) with source provenance. Numbers in dosages not misclassified as prices/quantities. | `engine/extractors.py` | `REG_11` | **VERIFIED** |
| **Package Isolation & AST** | Full package scan across all files verifying zero GT references; deep AST audit verifying pure in-memory execution in `engine/`. | `tests/test_safety_invariants.py`, `tests/test_remediation_regression.py` | `REG_12`, Invariants `INV_09`, `INV_10` | **VERIFIED** |

---

## 2. Modified Files & Change Rationale

1. `engine/extractors.py`: Prohibited image margins as separation gaps; added bounding box aspect evaluation; implemented physical coordinate indentation; strictly validated text_start/text_end; added financial and quantity boundary filters.
2. `engine/decision_engine.py`: Retained constituent records in `find_boundary_delimiters` when overlapping intervals merge; passed `bounding_boxes` to `compute_reliability_gates`.
3. `engine/matching.py`: Reversible reconstruction and character integrity verification.
4. `synthetic_cases/cases.py`: Updated expected HRS and W_active to reflect honest unobserved G5 state for single-line crops.
5. `tests/test_safety_invariants.py`: Updated INV_06 to test single-line (unobserved) vs multiline (valid) authentic crops; verified INV_09 and INV_10.
6. `tests/test_remediation_regression.py`: Comprehensive 12-test suite directly targeting all 8 Round 4 audit requirements.
7. `run_all.py`: Orchestrated verification suites, auto-generated reports and SHA256SUMS.txt.

---

## 3. Strict Operational Invariants Preserved
- **Zero Production Alteration:** Zero edits outside `phase_e1_1_isolated_engine/`.
- **Zero Ground Truth Access:** Ground truth files remain completely untouched and unaccessed.
- **Zero Experimental Inference:** No Zero-Shot, LOIOCV, or invoice evaluation has been started.
