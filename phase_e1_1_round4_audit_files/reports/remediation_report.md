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
