# Phase E1.1 Isolated Multi-Medicine Disentanglement Engine (Remediation Round 4)

## 1. Overview
This directory contains the independent, standalone software implementation of the **Stage E1.1 Disentanglement Decision Engine**, built strictly according to the approved frozen design specifications and remediated in Round 4.

The engine analyzes single or multi-line invoice rows, evaluates multi-faceted typographical, spatial, structural, financial, and raster geometric evidence, and emits a decoupled 4-axis decision tuple:
$$\mathcal{O} = (\text{Entity Type}, \; \text{Count Class}, \; \text{Boundary Status}, \; \text{Reconstruction Status})$$

---

## 2. Directory Structure
```
phase_e1_1_isolated_engine/
├── engine/
│   ├── __init__.py           # Package exports
│   ├── types.py              # Enums, Dataclasses, Output State Space
│   ├── extractors.py         # Signal extractors (EVID_01 to EVID_13), Gates, Envelope, Conflicts
│   ├── decision_engine.py    # Master HRS, 6-Step Gate Precedence, Compatibility Matrix
│   └── matching.py           # (m+n)x(m+n) Hungarian Bipartite Partial Matching & Metrics
├── synthetic_cases/
│   ├── __init__.py
│   └── cases.py              # Definitive specifications of TC_01 to TC_12
├── tests/
│   ├── test_synthetic_suite.py        # Execution runner for TC_01 to TC_12
│   ├── test_hungarian_matching.py     # True partial matching and cardinality verification
│   ├── test_safety_invariants.py      # 10 mandatory safety and architectural invariants
│   └── test_remediation_regression.py # 12 dedicated Round 4 engineering regression tests
├── reports/
│   ├── e1_1_implementation_and_test_report.md # Execution and verification report
│   └── remediation_report.md                  # Comprehensive Round 4 remediation report
├── run_all.py                # Master test orchestrator and checksum generator
├── implementation_trace.md   # Mathematical specification to code line mapping
├── test_results.json         # Full machine-readable test outputs
├── SHA256SUMS.txt            # SHA-256 hashes of all engine files
└── README.md                 # This documentation
```

---

## 3. How to Execute
Run the master test runner from powershell or command line:
```bash
python run_all.py
```
This executes:
0. Syntax & Compilation Verification across all 12 Python source files.
1. All 12 synthetic benchmark cases (`TC_01` to `TC_12`).
2. The augmented $(m+n) \times (m+n)$ Hungarian bipartite matching verification (8 tests).
3. The 10 safety and architectural invariant checks.
4. The 12 Round 4 engineering remediation regression tests.
5. Updates `test_results.json`, `reports/`, and `SHA256SUMS.txt`.

---

## 4. Strict Isolation & Compliance Notice
- **Zero Ground Truth Access:** The engine does not read, access, or import `e1_final_certified_ground_truth.csv` or `.json`.
- **Zero Production Modification:** No production files, `api_server.py`, or database instances were altered.
- **Purely Synthetic Validation:** Evaluation is confined strictly to the 12 synthetic test cases defined in the frozen specification.
