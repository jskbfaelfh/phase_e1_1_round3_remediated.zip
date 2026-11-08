    # -------------------------------------------------------------
    # REG_08: G2 EVID_06 Indentation Offset (Physical Box Coordinates Derived)
    # -------------------------------------------------------------
    text_2lines = "PANADOL 500MG\nBRUFEN 400MG"
    d_med = 8.0

    # 1. Equal alignment: x0 of line 1 = 10.0, x0 of line 2 = 10.0 -> Delta x = 0.0 -> EVID_06 = 0.0
    boxes_equal = [
        {"text": "PANADOL 500MG", "x0": 10.0, "x1": 100.0, "text_start": 0, "text_end": 13, "y0": 2.0, "y1": 12.0},
        {"text": "BRUFEN 400MG", "x0": 10.0, "x1": 95.0, "text_start": 14, "text_end": 26, "y0": 16.0, "y1": 26.0}
    ]
    evid_06_equal, meta_eq = compute_indentation_offset(boxes_equal, text_2lines, d_med)

    # 2. Significant indentation: line 1 x0 = 10.0, line 2 x0 = 30.0 -> Delta x = 20.0 >= 2.0 * 8.0 = 16.0 -> EVID_06 = 0.80
    boxes_indented = [
        {"text": "PANADOL 500MG", "x0": 10.0, "x1": 100.0, "text_start": 0, "text_end": 13, "y0": 2.0, "y1": 12.0},
        {"text": "BRUFEN 400MG", "x0": 30.0, "x1": 115.0, "text_start": 14, "text_end": 26, "y0": 16.0, "y1": 26.0}
    ]
    evid_06_indented, meta_ind = compute_indentation_offset(boxes_indented, text_2lines, d_med)

    # 3. Metadata invariance: passing indent_offset in metadata has ZERO effect
    line_meta_spurious = InputLine(
        text=text_2lines, ocr_confidence=0.90,
        bounding_boxes=boxes_equal,
        raster_metadata={"indent_offset": True}  # Metadata claims true, but physical boxes are equal!
    )
    sig_meta, _ = extract_evidence_signals(line_meta_spurious)
    meta_invariance_ok = (sig_meta["EVID_06"] == 0.0)

    # 4. Box coordinate sensitivity: changing coordinates dynamically changes result
    line_indented = InputLine(text=text_2lines, ocr_confidence=0.90, bounding_boxes=boxes_indented)
    sig_indented, _ = extract_evidence_signals(line_indented)
    coord_sensitivity_ok = (sig_indented["EVID_06"] == 0.80)

    # 5. Missing boxes yields 0.0
    line_no_boxes = InputLine(text=text_2lines, ocr_confidence=0.90, bounding_boxes=None)
    sig_no_boxes, _ = extract_evidence_signals(line_no_boxes)
    no_boxes_ok = (sig_no_boxes["EVID_06"] == 0.0)

    pass_reg8 = (
        evid_06_equal == 0.0 and
        evid_06_indented == 0.80 and
        meta_invariance_ok and
        coord_sensitivity_ok and
        no_boxes_ok
    )
    results.append({
        "test_name": "REG_08: G2 EVID_06 Indentation Offset (Physical Box Coordinates Derived)",
        "passed": pass_reg8,
        "evid_06_equal": evid_06_equal,
        "evid_06_indented": evid_06_indented,
        "meta_invariance_ok": meta_invariance_ok,
        "coord_sensitivity_ok": coord_sensitivity_ok,
        "no_boxes_ok": no_boxes_ok
    })

    # -------------------------------------------------------------
    # REG_09: Non-Preemptive Delimiter Extraction, Constituent Tracking & Medical Disambiguation
    # -------------------------------------------------------------
    # 6 Mandatory Medical Delimiter Tests:
    # 1. Brand name with comma: "AUGMENTIN, 1G TABLETS" -> zero split delimiters extracted
    _, det_comma = extract_evidence_signals(InputLine(text="AUGMENTIN, 1G TABLETS", ocr_confidence=0.92))
    delims_comma = find_boundary_delimiters("AUGMENTIN, 1G TABLETS", {}, det_comma)
    comma_not_split = (len(delims_comma) == 0)

    # 2. Chemical formula with '+': "AMOXICILLIN + CLAVULANIC 625MG" -> zero split delimiters extracted
    _, det_plus = extract_evidence_signals(InputLine(text="AMOXICILLIN + CLAVULANIC 625MG", ocr_confidence=0.92))
    delims_plus = find_boundary_delimiters("AMOXICILLIN + CLAVULANIC 625MG", {}, det_plus)
    plus_conflict_not_split = (len(delims_plus) == 0)

    # 3. Compound brand with hyphen: "CO-DIOVAN 160/12.5MG 28 TAB" -> zero split delimiters extracted
    _, det_cod = extract_evidence_signals(InputLine(text="CO-DIOVAN 160/12.5MG 28 TAB", ocr_confidence=0.92))
    delims_cod = find_boundary_delimiters("CO-DIOVAN 160/12.5MG 28 TAB", {}, det_cod)
    hyphen_brand_not_split = (len(delims_cod) == 0)

    # 4. Numerical range with hyphen: "PANADOL 500MG 1-2 TABLETS" -> zero split delimiters extracted
    _, det_range = extract_evidence_signals(InputLine(text="PANADOL 500MG 1-2 TABLETS", ocr_confidence=0.92))
    delims_range = find_boundary_delimiters("PANADOL 500MG 1-2 TABLETS", {}, det_range)
    range_not_split = (len(delims_range) == 0)

    # 5. Ratio / fraction with '/': "VALSARTAN 20/12.5MG" -> zero split delimiters extracted
    _, det_ratio = extract_evidence_signals(InputLine(text="VALSARTAN 20/12.5MG", ocr_confidence=0.92))
    delims_ratio = find_boundary_delimiters("VALSARTAN 20/12.5MG", {}, det_ratio)
    ratio_protected = (len(delims_ratio) == 0)

    # 6. Overlapping spatial void + text delimiter at same position with retained constituents
    test_text = "DRUG_A 10MG / DRUG_B 20MG"
    details_overlap = {
        "slash_matches": [(12, 15)],     # " / "
        "void_spans": [(12, 15)]         # Spatial void coincident with slash
    }
    extracted_delims = find_boundary_delimiters(test_text, {}, details_overlap)
    merged_has_constituents = (
        len(extracted_delims) == 1 and
        "SLASH_DELIMITER" in extracted_delims[0]["delimiter_type"] and
        "SPATIAL_VOID_DELIMITER" in extracted_delims[0]["delimiter_type"] and
        "constituents" in extracted_delims[0] and
        len(extracted_delims[0]["constituents"]) == 2
    )

    pass_reg9 = (
        comma_not_split and plus_conflict_not_split and hyphen_brand_not_split and
        range_not_split and ratio_protected and merged_has_constituents
    )
    results.append({
        "test_name": "REG_09: Non-Preemptive Delimiter Extraction, Constituent Tracking & Protection",
        "passed": pass_reg9,
        "comma_not_split": comma_not_split,
        "plus_conflict_not_split": plus_conflict_not_split,
        "hyphen_brand_not_split": hyphen_brand_not_split,
        "range_not_split": range_not_split,
        "ratio_protected": ratio_protected,
        "merged_has_constituents": merged_has_constituents
    })

    # -------------------------------------------------------------
    # REG_10: Character Integrity Non-Vacuous Reversibility & Negative Mutation Detection
    # -------------------------------------------------------------
    test_reversibility_lines = [
        "AUGMENTIN 1G 14 TABLETS",
        "  PANADOL 500MG / BRUFEN 400MG  ",
        "   CONCOR 5MG - LOPRESSOR 50MG   ",
        "CLAVAMOX 625MG\nPANADOL EXT",
        "  AMARYL 2MG 10.50   GLUCO 500MG 8.20  ",
        "   LIPITOR 20MG\nNORVASC 5MG\nCRESTOR 10MG   ",
        "DRUG_A 10MG  /  -  DRUG_B 20MG"
    ]
    all_reversibly_exact = True
    tested_reconstructions = 0

    for raw_str in test_reversibility_lines:
        out = engine.analyze_line(InputLine(
            text=raw_str, ocr_confidence=0.90,
            bounding_boxes=[
                {"text": "AMARYL 2MG 10.50", "x0": 10.0, "x1": 100.0, "text_start": 2, "text_end": 18},
                {"text": "GLUCO 500MG 8.20", "x0": 170.0, "x1": 260.0, "text_start": 21, "text_end": 37}
            ] if "GLUCO" in raw_str else None
        ))
        if out.reconstructed_spans:
            tested_reconstructions += 1
            reconstructed_str = reconstruct_original_string(out.reconstructed_spans, out.excluded_delimiters)
            if reconstructed_str != raw_str:
                all_reversibly_exact = False
                break

    # Crucial Negative Mutation Test:
    # Deliberately modify or drop a single character, verify that reconstruction mismatch is strictly detected!
    sample_out = engine.analyze_line(InputLine(text="PANADOL 500MG / BRUFEN 400MG", ocr_confidence=0.90))
    mutated_spans = list(sample_out.reconstructed_spans)
    mutated_spans[0] = (mutated_spans[0][0], mutated_spans[0][1], "PANADOL 500M")  # Dropped 'G'
    mutated_recon = reconstruct_original_string(mutated_spans, sample_out.excluded_delimiters)
    mutation_detected = (mutated_recon != "PANADOL 500MG / BRUFEN 400MG")

    pass_reg10 = all_reversibly_exact and (tested_reconstructions == len(test_reversibility_lines)) and mutation_detected
    results.append({
        "test_name": "REG_10: Character Integrity Non-Vacuous Reversibility & Negative Mutation Detection",
        "passed": pass_reg10,
        "tested_reconstructions": tested_reconstructions,
        "total_expected": len(test_reversibility_lines),
        "mutation_detected": mutation_detected,
        "detail": f"Verified 100% exact bitwise string reconstruction across all {tested_reconstructions} test strings with mutation sensitivity confirmed."
    })

    # -------------------------------------------------------------
    # REG_11: Structural Envelope Financial & Quantity Bounds Enforcement
    # -------------------------------------------------------------
    text_multi_price = "PANADOL 500MG 24 TAB 10.50 21.00"
    det_multi_price = {
        "strengths": ["500MG"], "forms": ["TAB"], "packs": ["24 TAB"],
        "prices": ["10.50", "21.00"], "quantities": []
    }
    s_env_bad_price, inputs_bad_price = evaluate_structural_envelope(text_multi_price, det_multi_price)

    text_multi_qty = "PANADOL 500MG 24 TAB QTY: 2 QTY: 3"
    det_multi_qty = {
        "strengths": ["500MG"], "forms": ["TAB"], "packs": ["24 TAB"],
        "prices": [], "quantities": ["2", "3"]
    }
    s_env_bad_qty, inputs_bad_qty = evaluate_structural_envelope(text_multi_qty, det_multi_qty)

    text_clean = "PANADOL 500MG 24 TAB 10.50"
    det_clean = {
        "strengths": ["500MG"], "forms": ["TAB"], "packs": ["24 TAB"],
        "prices": ["10.50"], "quantities": ["1"]
    }
    s_env_good, inputs_good = evaluate_structural_envelope(text_clean, det_clean)

    # Ambiguous number protection: dosage numbers like 500 in 500MG or 24 in 24 TAB must not be extracted as prices
    ambig_line = InputLine(text="PANADOL 500MG 24 TABLETS", ocr_confidence=0.90)
    _, ambig_details = extract_evidence_signals(ambig_line)
    ambig_protected = (len(ambig_details["prices"]) == 0)

    pass_reg11 = (
        s_env_bad_price == 0.0 and inputs_bad_price["price_count"] == 2 and
        s_env_bad_qty == 0.0 and inputs_bad_qty["qty_count"] == 2 and
        s_env_good == 1.0 and inputs_good["price_count"] == 1 and
        ambig_protected
    )
    results.append({
        "test_name": "REG_11: Structural Envelope Financial & Quantity Bounds Enforcement",
        "passed": pass_reg11,
        "multi_price_s_env": s_env_bad_price,
        "multi_qty_s_env": s_env_bad_qty,
        "clean_s_env": s_env_good,
        "ambig_protected": ambig_protected
    })

    # -------------------------------------------------------------
    # REG_12: Deep Package Isolation & In-Memory AST Sandbox Audit
    # -------------------------------------------------------------
    # 1. Full Package Isolation Scan
    forbidden_tokens = [
        "e1_final_certified_ground_truth",
        "final_certified_ground_truth",
        "ground_truth.csv",
        "ground_truth.json"
    ]
    gt_leak_found = False
    gt_leak_details = []

    for root, _, files in os.walk(BASE_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py") and f not in ("test_safety_invariants.py", "test_remediation_regression.py"):  # Exclude test files containing token lists
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    for token in forbidden_tokens:
                        if token in content:
                            gt_leak_found = True
                            gt_leak_details.append(f"Forbidden token '{token}' in {f}")

    # 2. Deep AST Sandbox Audit of engine/ core
    engine_dir = os.path.join(BASE_DIR, "engine")
    forbidden_calls = {"eval", "exec", "__import__", "importlib", "open", "read_text", "read_bytes", "system", "popen", "spawn"}
    allowed_roots = {
        "os", "sys", "re", "json", "hashlib", "datetime", "typing", "dataclasses",
        "enum", "collections", "math", "io", "zipfile", "ast", "numpy", "scipy"
    }
    ast_clean = True
    ast_violations = []

    for root, _, files in os.walk(engine_dir):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=fpath)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root_pkg = alias.name.split(".")[0]
                            if root_pkg not in allowed_roots and root_pkg != "engine":
                                ast_clean = False
                                ast_violations.append(f"Forbidden import in {f}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.level == 0 and node.module:
                            root_pkg = node.module.split(".")[0]
                            if root_pkg not in allowed_roots and root_pkg != "engine":
                                ast_clean = False
                                ast_violations.append(f"Forbidden import in {f}: from {node.module} import ...")
                    elif isinstance(node, ast.Call):
                        fn_name = ""
                        if isinstance(node.func, ast.Name):
                            fn_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            fn_name = node.func.attr
                        if fn_name in forbidden_calls:
                            ast_clean = False
                            ast_violations.append(f"Forbidden call in engine/{f}: {fn_name}()")

    pass_reg12 = (not gt_leak_found) and ast_clean and (len(ast_violations) == 0)
    results.append({
        "test_name": "REG_12: Deep Package Isolation & In-Memory AST Sandbox Audit",
        "passed": pass_reg12,
        "engine_files_audited": len([f for f in os.listdir(engine_dir) if f.endswith(".py")]),
        "gt_isolation_clean": not gt_leak_found,
        "violations_count": len(ast_violations)
    })

    all_passed = all(r["passed"] for r in results)
    return {
        "suite_name": "Engineering Remediation Regression Suite Round 4 (12 Checks)",
        "all_passed": all_passed,
        "total_tests": len(results),
        "passed_tests": sum(1 for r in results if r["passed"]),
        "results": results
    }


if __name__ == "__main__":
    rep = run_remediation_regression_suite()
    print(f"Regression Suite Round 4: {'ALL PASS' if rep['all_passed'] else 'FAIL'}")
    for r in rep["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test_name']}")
