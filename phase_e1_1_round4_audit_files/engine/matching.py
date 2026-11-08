"""
Stage E1.1 Disentanglement Decision Engine - Hungarian Bipartite Span Matching & Metrics
Frozen Specification Reference: e1_1_final_closure_amendment.md
Remediation Round 2
Includes:
  1. Augmented (m+n) x (m+n) block matrix Hungarian matching with M* = min(m, n) + 1.0.
  2. Span-level classification metrics (Precision, Recall/True Positive Rate, F1).
  3. Character-level integrity metrics (Preservation, Insertion Prevention, Order Preservation).
  4. Exact bit-for-bit raw text reconstruction and reversibility verification.
"""

import re
from collections import Counter
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Tuple, Dict, Any, Optional


def compute_span_iou(span_a: Tuple[int, int], span_b: Tuple[int, int]) -> float:
    """
    Computes Intersection-over-Union between two half-open character intervals [s, e).
    Strict numerical fidelity: returns exact raw unrounded float to prevent premature threshold rounding.
    """
    s_a, e_a = span_a
    s_b, e_b = span_b
    
    intersection = max(0, min(e_a, e_b) - max(s_a, s_b))
    len_a = max(0, e_a - s_a)
    len_b = max(0, e_b - s_b)
    union = len_a + len_b - intersection
    
    if union <= 0:
        return 0.0
    return float(intersection / union)


def optimal_hungarian_matching(
    pred_spans: List[Tuple[int, int]],
    gt_spans: List[Tuple[int, int]],
    tau_iou: float = 0.90
) -> Tuple[List[Tuple[int, int, float]], List[int], List[int]]:
    """
    Solves Maximum-Weight Bipartite Partial Matching under IoU >= tau_iou via
    the augmented (m+n) x (m+n) block matrix reduction to Minimum-Cost Perfect Matching.
    
    Guarantees:
      1. Maximum valid one-to-one matches (cardinality priority via M* = min(m, n) + 1.0).
      2. Maximum total IoU among maximum-cardinality matchings.
      3. No vertex is ever forced to pick an invalid edge (+10^6).
      4. Strict unrounded IoU threshold comparison (e.g. 0.89996 < 0.90 is rejected).
    """
    m = len(pred_spans)
    n = len(gt_spans)
    
    if m == 0 or n == 0:
        return [], [int(i) for i in range(m)], [int(j) for j in range(n)]
        
    # Cardinality priority bound M* = min(m, n) + 1.0
    m_star = float(min(m, n) + 1.0)
    penalty_invalid = 1e6
    dim = m + n
    
    # Construct (m+n) x (m+n) cost matrix
    cost_matrix = np.full((dim, dim), penalty_invalid, dtype=float)
    
    # 1. Primary Assignment Block C_{P, G} (m x n)
    for i, p_span in enumerate(pred_spans):
        for j, g_span in enumerate(gt_spans):
            iou = compute_span_iou(p_span, g_span)
            if iou >= tau_iou:
                cost_matrix[i, j] = -(m_star + iou)
                
    # 2. Prediction Slack Block C_{P, slack} (m x m)
    for i in range(m):
        cost_matrix[i, n + i] = 0.0
        
    # 3. Ground Truth Slack Block C_{slack, G} (n x n)
    for j in range(n):
        cost_matrix[m + j, j] = 0.0
        
    # 4. Inter-Slack Cancellation Block C_{slack, slack} (n x m)
    cost_matrix[m:, n:] = 0.0
    
    # Solve via linear_sum_assignment (Hungarian algorithm)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    matched_pairs = []
    matched_p = set()
    matched_g = set()
    
    for r, c in zip(row_ind, col_ind):
        # Valid assignment from pred (0..m-1) to GT (0..n-1) with negative cost
        if r < m and c < n and cost_matrix[r, c] < 0:
            iou = -cost_matrix[r, c] - m_star
            matched_pairs.append((int(r), int(c), float(iou)))
            matched_p.add(int(r))
            matched_g.add(int(c))
            
    unmatched_p = [int(i) for i in range(m) if i not in matched_p]
    unmatched_g = [int(j) for j in range(n) if j not in matched_g]
    
    return matched_pairs, unmatched_p, unmatched_g


def compute_levenshtein(s1: str, s2: str) -> int:
    """Computes exact Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return compute_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
        
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]


def reconstruct_original_string(
    reconstructed_spans: List[Tuple[int, int, str]],
    excluded_delimiters: List[Dict[str, Any]]
) -> str:
    """
    Reconstructs the original raw text string bit-for-bit by interleaving
    reconstructed entity spans and preserved delimiter records in positional order.
    """
    elements = []
    for span in reconstructed_spans:
        elements.append({
            "start": span[0],
            "end": span[1],
            "text": span[2]
        })
    for delim in excluded_delimiters:
        elements.append({
            "start": delim["start"],
            "end": delim["end"],
            "text": delim["text"]
        })
        
    elements.sort(key=lambda x: x["start"])
    return "".join(el["text"] for el in elements)


def evaluate_raw_character_integrity(orig_seq: str, recon_seq: str) -> Dict[str, Any]:
    """
    Rigorously verifies character-level text integrity across 3 distinct orthogonal tests:
      1. Character Preservation: Zero characters from original text are lost.
         (Multiset check: every char in orig appears in recon with count >= orig count)
      2. Character Insertion Prevention: Zero phantom characters are injected.
         (Multiset check: no char appears in recon with count > orig count, and no unknown chars)
      3. Character Order Preservation: Relative sequence of characters is maintained.
         (Subsequence check: preserved characters appear in the exact relative sequence)
    """
    orig_counts = Counter(orig_seq)
    recon_counts = Counter(recon_seq)
    
    # Test 1: Preservation (No drops / deletions)
    char_preservation_passed = all(recon_counts[c] >= count for c, count in orig_counts.items())
    
    # Test 2: Insertion Prevention (No phantom insertions)
    char_insertion_passed = all(orig_counts[c] >= count for c, count in recon_counts.items())
    
    # Test 3: Order Preservation (Non-inverted relative order)
    orig_ptr = 0
    order_preserved = True
    for ch in recon_seq:
        if ch in orig_counts:
            next_idx = orig_seq.find(ch, orig_ptr)
            if next_idx == -1:
                order_preserved = False
                break
            orig_ptr = next_idx + 1
            
    return {
        "char_preservation_passed": bool(char_preservation_passed),
        "char_insertion_passed": bool(char_insertion_passed),
        "char_order_passed": bool(order_preserved),
        "original_len": len(orig_seq),
        "reconstructed_len": len(recon_seq)
    }


def compute_character_integrity(
    original_text: str,
    reconstructed_spans: List[Tuple[int, int, str]],
    excluded_delimiters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Verifies 100% character integrity and bitwise reversibility between original raw line,
    reconstructed entities, and preserved excluded delimiters (Defect G Fix).
    
    Guarantees:
      1. Reversibility: Reconstructed string from spans + delimiters strictly matches original text.
      2. Preservation: Zero characters from raw line are lost across entities + delimiters.
      3. Insertion Prevention: Zero phantom characters injected.
      4. Order Preservation: Exact character ordering is maintained.
    """
    if excluded_delimiters is None:
        excluded_delimiters = []
        
    reconstructed_full = reconstruct_original_string(reconstructed_spans, excluded_delimiters)
    is_exact_match = (reconstructed_full == original_text)
    
    raw_eval = evaluate_raw_character_integrity(original_text, reconstructed_full)
    
    # Also evaluate semantic payload alphanumeric integrity
    orig_alnum = "".join(c for c in original_text if c.isalnum())
    recon_entities_alnum = "".join(c for span in reconstructed_spans for c in span[2] if c.isalnum())
    alnum_eval = evaluate_raw_character_integrity(orig_alnum, recon_entities_alnum)
    
    return {
        "is_reversibly_exact": bool(is_exact_match),
        "char_preservation_passed": bool(raw_eval["char_preservation_passed"] and alnum_eval["char_preservation_passed"]),
        "char_insertion_passed": bool(raw_eval["char_insertion_passed"] and alnum_eval["char_insertion_passed"]),
        "char_order_passed": bool(raw_eval["char_order_passed"] and alnum_eval["char_order_passed"]),
        "orig_len": len(original_text),
        "recon_len": len(reconstructed_full),
        "levenshtein_distance": compute_levenshtein(original_text, reconstructed_full),
        "excluded_delimiters_count": len(excluded_delimiters)
    }


def compute_span_metrics(
    all_matched_pairs: List[Tuple[int, int, float]],
    total_pred_count: int,
    total_gt_count: int
) -> Dict[str, Any]:
    """
    Computes Precision, Recall (True Positive Rate for span classification), and F1.
    """
    tp = len(all_matched_pairs)
    fp = total_pred_count - tp
    fn = total_gt_count - tp
    
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
    
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = (2 * precision * recall) / (precision + recall)
    else:
        f1 = None
        
    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "precision": round(precision, 4) if precision is not None else "N/A",
        "recall": round(recall, 4) if recall is not None else "N/A",
        "recall_span_tpr": round(recall, 4) if recall is not None else "N/A",
        "f1": round(f1, 4) if f1 is not None else "N/A"
    }
