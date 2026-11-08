"""
Stage E1.1 Synthetic Test Cases Execution Suite
Validates TC_01 to TC_12 against the frozen specification.
"""

import os
import sys
import math
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.decision_engine import DisentanglementDecisionEngine
from synthetic_cases.cases import SYNTHETIC_TEST_CASES


def run_synthetic_suite() -> Dict[str, Any]:
    engine = DisentanglementDecisionEngine()
    results = []
    all_passed = True
    
    for case in SYNTHETIC_TEST_CASES:
        case_id = case["case_id"]
        input_line = case["input_line"]
        
        # Execute decision engine
        output = engine.analyze_line(input_line)
        
        # Check assertions
        pass_entity = (output.axis1_entity_type == case["expected_entity_type"])
        pass_count = (output.axis2_count_class == case["expected_count_class"])
        pass_boundary = (output.axis3_boundary_status == case["expected_boundary_status"])
        pass_recon = (output.axis4_reconstruction_status == case["expected_reconstruction_status"])
        
        pass_hrs = math.isclose(output.hrs_score, case["expected_hrs"], abs_tol=0.005)
        pass_w_act = math.isclose(output.w_active, case["expected_w_active"], abs_tol=0.005)
        pass_p_conf = math.isclose(output.p_conflict, case["expected_p_conflict"], abs_tol=0.005)
        pass_path = (output.precedence_path == case["expected_precedence_path"])
        
        case_passed = (
            pass_entity and pass_count and pass_boundary and pass_recon and
            pass_hrs and pass_w_act and pass_p_conf and pass_path
        )
        
        if not case_passed:
            all_passed = False
            
        case_result = {
            "case_id": case_id,
            "description": case["description"],
            "input_text": input_line.text,
            "passed": case_passed,
            "actual": {
                "entity_type": output.axis1_entity_type.value,
                "count_class": output.axis2_count_class.value,
                "boundary_status": output.axis3_boundary_status.value,
                "reconstruction_status": output.axis4_reconstruction_status.value,
                "hrs_score": output.hrs_score,
                "s_norm": output.s_norm,
                "w_active": output.w_active,
                "p_conflict": output.p_conflict,
                "s_env": output.s_env,
                "n_multi": output.n_multi,
                "precedence_path": output.precedence_path,
                "reconstructed_spans": output.reconstructed_spans,
                "decision_reasons": output.decision_reasons
            },
            "expected": {
                "entity_type": case["expected_entity_type"].value,
                "count_class": case["expected_count_class"].value,
                "boundary_status": case["expected_boundary_status"].value,
                "reconstruction_status": case["expected_reconstruction_status"].value,
                "hrs_score": case["expected_hrs"],
                "w_active": case["expected_w_active"],
                "p_conflict": case["expected_p_conflict"],
                "precedence_path": case["expected_precedence_path"]
            },
            "checks": {
                "pass_entity": pass_entity,
                "pass_count": pass_count,
                "pass_boundary": pass_boundary,
                "pass_recon": pass_recon,
                "pass_hrs": pass_hrs,
                "pass_w_act": pass_w_act,
                "pass_p_conf": pass_p_conf,
                "pass_path": pass_path
            }
        }
        results.append(case_result)
        
    return {
        "suite_name": "E1.1 Synthetic Benchmark Suite (TC_01 to TC_12)",
        "total_cases": len(SYNTHETIC_TEST_CASES),
        "passed_cases": sum(1 for r in results if r["passed"]),
        "failed_cases": sum(1 for r in results if not r["passed"]),
        "all_passed": all_passed,
        "results": results
    }


if __name__ == "__main__":
    report = run_synthetic_suite()
    print(f"Suite: {report['suite_name']}")
    print(f"Passed: {report['passed_cases']}/{report['total_cases']}")
    for r in report["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['case_id']}: {r['description']}")
        if not r["passed"]:
            print(f"  Expected: {r['expected']}")
            print(f"  Actual:   {r['actual']}")
