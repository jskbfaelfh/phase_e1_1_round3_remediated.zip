# Phase E1.1 Engineering Remediation Report — Round 5
**Date:** `2026-11-11T11:09:58.249703`  
**Status:** `ROUND_5_REMEDIATION_IMPLEMENTED — INDEPENDENT_REAUDIT_REQUIRED`  

---

## 1. Summary of Defect Remediations and Independent Proofs (Round 5)

| Audit Item | Remediated Defect | Implementation File & Line | Regression Verification Test | Status |
|:---|:---|:---|:---|:---:|
| **Multiplicity Gate Integrity** | Prevented declaring DISENTANGLED_BOUNDARY or emitting 1 entity when MULTIPLE_MEDICINES is decided. Emits ABSTAIN_UNSUPPORTED_BOUNDARY with zero false entities per specification matrix. | `engine/decision_engine.py` | `REG_08`, `REG_09` | **VERIFIED** |
| **q_aspect from Crop Dims** | Prohibited awarding q_aspect=1.0 based on crop dimensions alone. Missing OCR boxes strictly yield q_aspect=0.0 and GEOM_UNOBSERVED. | `engine/extractors.py` | `REG_01`, `REG_06` | **VERIFIED** |
| **Multi-Line Aspect Grouping** | Grouped OCR boxes by line/baseline before checking horizontal overlap. Boxes on different lines naturally overlap in x and are no longer marked touching/overlapping. | `engine/extractors.py` | `REG_03` | **VERIFIED** |
| **Indentation Fixed Thresholds** | Removed fixed thresholds 16.0 and 4.0 from `compute_indentation_offset`. Requires valid d_med and valid Y coordinates, otherwise strictly UNOBSERVED. | `engine/extractors.py` | `REG_02`, `REG_04` | **VERIFIED** |
| **Skew Angle Geometry** | Pure pixel geometry for skew measurement; returns None when unobservable. | `engine/extractors.py` | `REG_05` | **VERIFIED** |
| **Void Spans Across Lines** | Bounding box void_spans evaluated strictly within the same line, preventing false boundary creation across line breaks. | `engine/extractors.py` | `REG_10` | **VERIFIED** |
| **Output State Consistency** | validate_output_compatibility strictly forbids contradictory states across all 4 axes. | `engine/decision_engine.py`, `engine/types.py` | `REG_12` | **VERIFIED** |
| **Lexicon & Ratio Protection** | Protected brand names with hyphens/commas, chemical formulas (+), and fixed-dose combination ratios (160/12.5MG). | `engine/extractors.py`, `engine/decision_engine.py` | `REG_13` | **VERIFIED** |
| **Character Conservation** | 100% bitwise reversible text reconstruction with single-character mutation detection. | `engine/matching.py`, `tests/test_remediation_regression.py` | `REG_14`, Invariant `INV_05` | **VERIFIED** |

---

## 2. Modified Files & Change Rationale

1. `engine/extractors.py`: Prohibited image crop dimensions as aspect substitute; added multi-line box grouping in `evaluate_bounding_boxes_aspect`; eliminated 16.0 and 4.0 fixed thresholds in `compute_indentation_offset`; restricted `void_spans` to same-line boxes.
2. `engine/decision_engine.py`: Step 4 and Step 6 updated to emit `ABSTAIN_UNSUPPORTED_BOUNDARY` with zero spans when boundary cuts are unsupported or absent; added multi-axis consistency checks in `validate_output_compatibility`.
3. `engine/types.py`: Harmonized `MEDICINE_ENTRY` and `MEDICINE_ROW` support; added `ABSTAIN_AMBIGUOUS_BOUNDARY` to `BoundaryStatus`.
4. `synthetic_cases/cases.py`: Provided authentic multi-line bounding boxes for TC_05 and TC_09 to support genuine physical aspect evaluation.
5. `tests/test_remediation_regression.py`: Comprehensive 14-test suite directly targeting all 14 Round 5 requirements.
6. `run_all.py`: Orchestrated complete verification, auto-generated reports and SHA256SUMS.txt.

---

## 3. Strict Operational Invariants Preserved
- **Zero Production Alteration:** Zero edits outside `phase_e1_1_isolated_engine/`.
- **Zero Ground Truth Access:** Ground truth files remain completely untouched and unaccessed.
- **Zero Experimental Inference:** No Zero-Shot, LOIOCV, or invoice evaluation has been started.
