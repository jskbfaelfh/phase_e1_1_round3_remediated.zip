"""
Stage E1.1 Hungarian Bipartite Matching Verification Suite
Tests the augmented (m+n) x (m+n) block matrix implementation, boundary precision, and partial matching properties.
"""

import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.matching import optimal_hungarian_matching, compute_span_iou, compute_span_metrics


def run_hungarian_tests():
    test_results = []
    
    # -------------------------------------------------------------
    # Test 1: m = n = 2 with exactly ONE valid edge (True Partial Matching)
    # -------------------------------------------------------------
    pred_spans_1 = [(0, 10), (12, 20)]
    gt_spans_1 = [(0, 10), (25, 35)]
    
    matched_pairs, unmatched_p, unmatched_g = optimal_hungarian_matching(pred_spans_1, gt_spans_1, tau_iou=0.90)
    
    pass_t1 = (
        len(matched_pairs) == 1 and
        matched_pairs[0][0] == 0 and matched_pairs[0][1] == 0 and
        unmatched_p == [1] and
        unmatched_g == [1]
    )
    test_results.append({
        "test_name": "T1: True Partial Matching (m=n=2, only 1 valid edge)",
        "passed": pass_t1,
        "matched_pairs": matched_pairs,
        "unmatched_p": unmatched_p,
        "unmatched_g": unmatched_g
    })
    
    # -------------------------------------------------------------
    # Test 2: Cardinality Dominance via M*
    # -------------------------------------------------------------
    pred_spans_2 = [(0, 10), (10, 20)]
    gt_spans_2 = [(0, 10), (10, 20)]
    
    matched_2, un_p_2, un_g_2 = optimal_hungarian_matching(pred_spans_2, gt_spans_2, tau_iou=0.90)
    pass_t2 = (len(matched_2) == 2 and len(un_p_2) == 0 and len(un_g_2) == 0)
    test_results.append({
        "test_name": "T2: Cardinality Dominance (M* maximizes match count)",
        "passed": pass_t2,
        "matched_pairs": matched_2
    })
    
    # -------------------------------------------------------------
    # Test 3: Zero Valid Matches
    # -------------------------------------------------------------
    pred_spans_3 = [(0, 5), (10, 15)]
    gt_spans_3 = [(20, 30), (40, 50)]
    
    matched_3, un_p_3, un_g_3 = optimal_hungarian_matching(pred_spans_3, gt_spans_3, tau_iou=0.90)
    pass_t3 = (len(matched_3) == 0 and un_p_3 == [0, 1] and un_g_3 == [0, 1])
    test_results.append({
        "test_name": "T3: Zero Valid Matches (Clean All-Slack Pairing)",
        "passed": pass_t3,
        "unmatched_p": un_p_3,
        "unmatched_g": un_g_3
    })
    
    # -------------------------------------------------------------
    # Test 4: Metrics Calculation
    # -------------------------------------------------------------
    metrics = compute_span_metrics(matched_pairs, len(pred_spans_1), len(gt_spans_1))
    pass_t4 = (metrics["precision"] == 0.5 and metrics["recall"] == 0.5 and metrics["f1"] == 0.5)
    test_results.append({
        "test_name": "T4: Metrics Calculation (P=0.5, R=0.5, F1=0.5)",
        "passed": pass_t4,
        "metrics": metrics
    })
    
    # -------------------------------------------------------------
    # Test 5: Strict Unrounded IoU Rejection at 0.89996 < 0.90
    # -------------------------------------------------------------
    # Span pair with exact IoU = 0.89996
    # Let union = 100,000, intersection = 89,996 -> IoU = 0.89996
    p_span_near = (0, 89996)
    g_span_near = (0, 100000)
    iou_near = compute_span_iou(p_span_near, g_span_near)
    matched_near, un_p_near, un_g_near = optimal_hungarian_matching([p_span_near], [g_span_near], tau_iou=0.90)
    pass_t5 = (iou_near < 0.90 and len(matched_near) == 0 and un_p_near == [0] and un_g_near == [0])
    test_results.append({
        "test_name": f"T5: IoU Boundary Rejection (IoU={iou_near:.5f} < 0.90 strictly rejected)",
        "passed": pass_t5,
        "iou_calculated": iou_near,
        "matched_count": len(matched_near)
    })
    
    # -------------------------------------------------------------
    # Test 6: Strict IoU Acceptance at exactly 0.90000
    # -------------------------------------------------------------
    # Let intersection = 90, union = 100 -> IoU = 0.90000
    p_span_exact = (0, 90)
    g_span_exact = (0, 100)
    iou_exact = compute_span_iou(p_span_exact, g_span_exact)
    matched_exact, un_p_exact, un_g_exact = optimal_hungarian_matching([p_span_exact], [g_span_exact], tau_iou=0.90)
    pass_t6 = (iou_exact == 0.90 and len(matched_exact) == 1 and matched_exact[0][0] == 0)
    test_results.append({
        "test_name": f"T6: IoU Boundary Acceptance (IoU={iou_exact:.5f} == 0.90 accepted)",
        "passed": pass_t6,
        "iou_calculated": iou_exact,
        "matched_count": len(matched_exact)
    })
    
    # -------------------------------------------------------------
    # Test 7: Empty Inputs Handling
    # -------------------------------------------------------------
    m_empty1, u_p1, u_g1 = optimal_hungarian_matching([], [(0, 10)])
    m_empty2, u_p2, u_g2 = optimal_hungarian_matching([(0, 10)], [])
    m_empty3, u_p3, u_g3 = optimal_hungarian_matching([], [])
    pass_t7 = (
        len(m_empty1) == 0 and u_g1 == [0] and
        len(m_empty2) == 0 and u_p2 == [0] and
        len(m_empty3) == 0 and len(u_p3) == 0 and len(u_g3) == 0
    )
    test_results.append({
        "test_name": "T7: Empty Inputs Handling (Clean Zero Returns)",
        "passed": pass_t7
    })
    
    # -------------------------------------------------------------
    # Test 8: Unbalanced Dimensions (m != n)
    # -------------------------------------------------------------
    # 3 predictions, 1 ground truth matching P2
    pred_unbal = [(0, 5), (10, 20), (30, 35)]
    gt_unbal = [(10, 20)]
    m_unbal, u_p_unbal, u_g_unbal = optimal_hungarian_matching(pred_unbal, gt_unbal, tau_iou=0.90)
    pass_t8 = (
        len(m_unbal) == 1 and m_unbal[0] == (1, 0, 1.0) and
        set(u_p_unbal) == {0, 2} and len(u_g_unbal) == 0
    )
    test_results.append({
        "test_name": "T8: Unbalanced Dimensions (m=3, n=1 with P2 <-> G1)",
        "passed": pass_t8
    })
    
    all_passed = all(t["passed"] for t in test_results)
    return {
        "suite_name": "Hungarian Augmented Block Matrix Tests",
        "all_passed": all_passed,
        "tests": test_results
    }


if __name__ == "__main__":
    res = run_hungarian_tests()
    print(f"Hungarian Tests: {'ALL PASS' if res['all_passed'] else 'FAIL'}")
    for t in res["tests"]:
        print(f"  [{'PASS' if t['passed'] else 'FAIL'}] {t['test_name']}")
