"""
Stage E1.1 Synthetic Test Cases Definition (TC_01 to TC_12)
Frozen Specification Reference: e1_1_final_closure_amendment.md
Remediation Round 3
Includes authentic 2D pixel crops for G5 raster processing and complete bounding boxes for G2.
All metadata 'q_geo' overrides removed (G5 strictly derived from 2D pixel analysis).
"""

from typing import List, Dict, Any
import numpy as np
from engine.types import (
    InputLine, EntityType, CountClass, BoundaryStatus, ReconstructionStatus
)


def create_single_line_pixel_crop(height: int = 16, width: int = 200) -> np.ndarray:
    """
    Creates an authentic 2D grayscale image crop (0=black ink, 255=white paper)
    containing a single horizontal text baseline in rows 5..11.
    """
    img = np.full((height, width), 255, dtype=np.uint8)
    img[5:12, 10:190] = 30  # Dark ink pixels
    return img


def create_multiline_pixel_crop(lines: int = 2, width: int = 200) -> np.ndarray:
    """
    Creates an authentic 2D grayscale image crop containing multiple physical text lines
    separated by blank white inter-line pixel valleys.
    """
    line_h = 8
    valley_h = 6
    total_h = lines * line_h + (lines - 1) * valley_h + 8
    img = np.full((total_h, width), 255, dtype=np.uint8)
    
    y = 4
    for _ in range(lines):
        img[y:y + line_h, 10:190] = 30  # Ink text pixels
        y += line_h + valley_h
    return img


SYNTHETIC_TEST_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "TC_01",
        "description": "Clean single medicine with cohesive structural envelope",
        "input_line": InputLine(
            text="AUGMENTIN 1G 14 TABLETS",
            ocr_confidence=0.94,
            image_crop=create_single_line_pixel_crop(),
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.SINGLE_MEDICINE,
        "expected_boundary_status": BoundaryStatus.NO_SPLIT_REQUIRED,
        "expected_reconstruction_status": ReconstructionStatus.RECONSTRUCTED_SINGLE,
        "expected_hrs": 0.000,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 5: Definitive Singleness Gate"
    },
    {
        "case_id": "TC_02",
        "description": "Multi-medicine with explicit slash separator and repeated dosage form",
        "input_line": InputLine(
            text="PANADOL 500MG / BRUFEN 400MG",
            ocr_confidence=0.92,
            image_crop=create_single_line_pixel_crop(),
            bounding_boxes=[
                {"text": "PANADOL", "text_start": 0, "text_end": 7, "x0": 10.0, "x1": 66.0},
                {"text": "500MG", "text_start": 8, "text_end": 13, "x0": 74.0, "x1": 114.0},
                {"text": "/", "text_start": 14, "text_end": 15, "x0": 136.0, "x1": 144.0},
                {"text": "BRUFEN", "text_start": 16, "text_end": 22, "x0": 166.0, "x1": 222.0},
                {"text": "400MG", "text_start": 23, "text_end": 28, "x0": 230.0, "x1": 270.0}
            ],
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.MULTIPLE_MEDICINES,
        "expected_boundary_status": BoundaryStatus.DISENTANGLED_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.RECONSTRUCTED_MULTI,
        "expected_hrs": 0.833,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 4: Definitive Multiplicity Gate"
    },
    {
        "case_id": "TC_03",
        "description": "Multi-medicine with spatial void and dual financial price columns",
        "input_line": InputLine(
            text="AMARYL 2MG 10.50   GLUCO 500MG 8.20",
            ocr_confidence=0.88,
            image_crop=create_single_line_pixel_crop(),
            bounding_boxes=[
                {"text": "AMARYL", "text_start": 0, "text_end": 6, "x0": 10.0, "x1": 58.0},
                {"text": "2MG", "text_start": 7, "text_end": 10, "x0": 66.0, "x1": 90.0},
                {"text": "10.50", "text_start": 11, "text_end": 16, "x0": 98.0, "x1": 138.0},
                {"text": "GLUCO", "text_start": 19, "text_end": 24, "x0": 202.0, "x1": 242.0},  # gap = 64px >= 2.5 * 8.0 = 20px
                {"text": "500MG", "text_start": 25, "text_end": 30, "x0": 250.0, "x1": 290.0},
                {"text": "8.20", "text_start": 31, "text_end": 35, "x0": 298.0, "x1": 330.0}
            ],
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.DISENTANGLED_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.PROVISIONAL_RECONSTRUCTION,
        "expected_hrs": 0.500,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 6: Residual Provisional State"
    },
    {
        "case_id": "TC_04",
        "description": "Chemical combination with conjunction symbol and shared strength (active conflict)",
        "input_line": InputLine(
            text="AMOXICILLIN + CLAVULANIC 625MG",
            ocr_confidence=0.91,
            image_crop=create_single_line_pixel_crop(),
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT,
        "expected_reconstruction_status": ReconstructionStatus.ABSTAIN_SEGMENTATION,
        "expected_hrs": 0.000,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.40,
        "expected_precedence_path": "Step 3: Active Conflict Gate"
    },
    {
        "case_id": "TC_05",
        "description": "Degraded OCR with physical vertical line stacking in raster",
        "input_line": InputLine(
            text="CLAVAMOX 625MG\nPANADOL EXT",
            ocr_confidence=0.55,
            image_crop=create_multiline_pixel_crop(lines=2),
            bounding_boxes=[
                {"text": "CLAVAMOX 625MG", "text_start": 0, "text_end": 14, "x0": 5.0, "x1": 120.0, "y0": 2.0, "y1": 10.0},
                {"text": "PANADOL EXT", "text_start": 15, "text_end": 26, "x0": 5.0, "x1": 100.0, "y0": 16.0, "y1": 24.0}
            ],
            raster_metadata={
                "observed": True,
                "skew_angle": 0.8,
                "line_gap": 4.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.PROVISIONAL_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.PROVISIONAL_RECONSTRUCTION,
        "expected_hrs": 0.206,
        "expected_w_active": 0.486,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 6: Residual Provisional State"
    },
    {
        "case_id": "TC_06",
        "description": "Fused text with repeated strengths and zero spatial/punctuation delimiters",
        "input_line": InputLine(
            text="CATAFLAM50MGVOLTAREN100MG",
            ocr_confidence=0.89,
            image_crop=None,
            raster_metadata=None  # GEOM_UNOBSERVED
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.ABSTAIN_UNSUPPORTED_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.ABSTAIN_SEGMENTATION,
        "expected_hrs": 0.222,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 6: Residual Provisional State"
    },
    {
        "case_id": "TC_07",
        "description": "Administrative non-medicine accounting header",
        "input_line": InputLine(
            text="TOTAL AMOUNT DUE / CASH: 245.50",
            ocr_confidence=0.95,
            image_crop=create_single_line_pixel_crop(),
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.NON_MEDICINE_TEXT,
        "expected_count_class": CountClass.NON_APPLICABLE,
        "expected_boundary_status": BoundaryStatus.NON_APPLICABLE,
        "expected_reconstruction_status": ReconstructionStatus.NON_APPLICABLE,
        "expected_hrs": 0.000,
        "expected_w_active": 0.000,  # Honest unmeasured capacity in pre-emption
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 1: Entity Type Pre-emption"
    },
    {
        "case_id": "TC_08",
        "description": "Bare unanchored single word without dosage envelope markers",
        "input_line": InputLine(
            text="ASPIRIN",
            ocr_confidence=0.85,
            image_crop=None,
            raster_metadata=None  # GEOM_UNOBSERVED
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.NO_SPLIT_REQUIRED,
        "expected_reconstruction_status": ReconstructionStatus.PROVISIONAL_RECONSTRUCTION,
        "expected_hrs": 0.000,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 6: Residual Provisional State"
    },
    {
        "case_id": "TC_09",
        "description": "Triple stacked vertical medicine lines with subline baselines",
        "input_line": InputLine(
            text="LIPITOR 20MG\nNORVASC 5MG\nCRESTOR 10MG",
            ocr_confidence=0.91,
            image_crop=create_multiline_pixel_crop(lines=3),
            bounding_boxes=[
                {"text": "LIPITOR 20MG", "text_start": 0, "text_end": 12, "x0": 5.0, "x1": 110.0, "y0": 2.0, "y1": 10.0},
                {"text": "NORVASC 5MG", "text_start": 13, "text_end": 24, "x0": 5.0, "x1": 105.0, "y0": 16.0, "y1": 24.0},
                {"text": "CRESTOR 10MG", "text_start": 25, "text_end": 37, "x0": 5.0, "x1": 115.0, "y0": 30.0, "y1": 38.0}
            ],
            raster_metadata={
                "observed": True,
                "skew_angle": 0.2,
                "line_gap": 4.5,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.DISENTANGLED_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.PROVISIONAL_RECONSTRUCTION,
        "expected_hrs": 0.300,
        "expected_w_active": 1.000,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 6: Residual Provisional State"
    },
    {
        "case_id": "TC_10",
        "description": "Multi-medicine separated by spaced hyphen dash and repeated strength",
        "input_line": InputLine(
            text="CONCOR 5MG - LOPRESSOR 50MG",
            ocr_confidence=0.90,
            image_crop=create_single_line_pixel_crop(),
            bounding_boxes=[
                {"text": "CONCOR", "text_start": 0, "text_end": 6, "x0": 10.0, "x1": 58.0},
                {"text": "5MG", "text_start": 7, "text_end": 10, "x0": 66.0, "x1": 90.0},
                {"text": "-", "text_start": 11, "text_end": 12, "x0": 112.0, "x1": 120.0},
                {"text": "LOPRESSOR", "text_start": 13, "text_end": 22, "x0": 142.0, "x1": 214.0},
                {"text": "50MG", "text_start": 23, "text_end": 27, "x0": 222.0, "x1": 254.0}
            ],
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.MULTIPLE_MEDICINES,
        "expected_boundary_status": BoundaryStatus.DISENTANGLED_BOUNDARY,
        "expected_reconstruction_status": ReconstructionStatus.RECONSTRUCTED_MULTI,
        "expected_hrs": 0.800,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 4: Definitive Multiplicity Gate"
    },
    {
        "case_id": "TC_11",
        "description": "Hyphenated brand name with embedded dosage ratio (active conflict)",
        "input_line": InputLine(
            text="CO-DIOVAN 160/12.5MG 28 TAB",
            ocr_confidence=0.93,
            image_crop=create_single_line_pixel_crop(),
            raster_metadata={
                "observed": True,
                "skew_angle": 0.5,
                "line_gap": 0.0,
                "line_height": 12.0,
                "aspect_valid": True,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.PROVISIONAL_COUNT,
        "expected_boundary_status": BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT,
        "expected_reconstruction_status": ReconstructionStatus.ABSTAIN_SEGMENTATION,
        "expected_hrs": 0.000,
        "expected_w_active": 0.900,
        "expected_p_conflict": 0.35,
        "expected_precedence_path": "Step 3: Active Conflict Gate"
    },
    {
        "case_id": "TC_12",
        "description": "Severely degraded raster noise below active measurement capacity floor",
        "input_line": InputLine(
            text="~..X% 20M? // ??",
            ocr_confidence=0.32,
            image_crop=create_single_line_pixel_crop(),
            raster_metadata={
                "observed": True,
                "skew_angle": 4.0,
                "line_gap": 1.0,
                "line_height": 10.0,
                "aspect_valid": False,
                "degenerate": False
            }
        ),
        "expected_entity_type": EntityType.MEDICINE_ROW,
        "expected_count_class": CountClass.ABSTAIN_COUNT,
        "expected_boundary_status": BoundaryStatus.ABSTAIN_UNRESOLVED_CONFLICT,
        "expected_reconstruction_status": ReconstructionStatus.ABSTAIN_SEGMENTATION,
        "expected_hrs": 0.000,
        "expected_w_active": 0.000,
        "expected_p_conflict": 0.00,
        "expected_precedence_path": "Step 2: Capacity Noise Gate"
    }
]
