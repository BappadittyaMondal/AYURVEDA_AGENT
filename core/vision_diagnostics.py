"""
core/vision_diagnostics.py - Core Engine for Phase 40: Computer Vision Optical Diagnostics Pipeline.
Performs CIELAB color-space calibration, tongue coating percentage evaluation, and scleral icterus detection.
"""

import time
import uuid
import math
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.vision_diagnostics import (
    AnatomicalTarget,
    ColorCardStandard,
    CalibrationTargetCreate,
    CalibrationTargetRecord,
    OpticalInferenceRequest,
    OpticalInferenceResult,
)
from models.schemas import UserResponse


class VisionDiagnosticError(Exception):
    pass


def seed_default_calibration_targets(conn: sqlite3.Connection) -> None:
    """Seeds baseline hospital color-calibration reference standards."""
    now = int(time.time())
    defaults = [
        ("TARGET-GREY-18", ColorCardStandard.HOSPITAL_NEUTRAL_GREY.value, 50.0, 0.0, 0.0, 2.0),
        ("TARGET-XRITE-NEUTRAL5", ColorCardStandard.X_RITE_COLORCHECKER.value, 50.8, -0.1, -0.5, 2.0)
    ]
    cursor = conn.cursor()
    for tid, std, l, a, b, tol in defaults:
        cursor.execute(
            """
            INSERT OR IGNORE INTO optical_calibration_targets (
                target_id, color_card_standard, reference_l, reference_a, reference_b, tolerance_delta_e, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (tid, std, l, a, b, tol, now)
        )
    conn.commit()


def compute_cielab_delta_e(l1: float, a1: float, b1: float, l2: float, a2: float, b2: float) -> float:
    """Calculates standard CIE76 Euclidean color difference Delta E*ab."""
    return round(math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2), 3)


def create_calibration_target(
    target_in: CalibrationTargetCreate,
    conn: Optional[sqlite3.Connection] = None
) -> CalibrationTargetRecord:
    """Registers a new physical optical calibration target."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO optical_calibration_targets (
                target_id, color_card_standard, reference_l, reference_a, reference_b, tolerance_delta_e, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_id) DO UPDATE SET
                color_card_standard=excluded.color_card_standard,
                reference_l=excluded.reference_l,
                reference_a=excluded.reference_a,
                reference_b=excluded.reference_b,
                tolerance_delta_e=excluded.tolerance_delta_e;
            """,
            (
                target_in.target_id,
                target_in.color_card_standard.value,
                target_in.reference_l,
                target_in.reference_a,
                target_in.reference_b,
                target_in.tolerance_delta_e,
                now,
            )
        )
        conn.commit()
        return get_calibration_target(target_in.target_id, conn=conn)
    finally:
        if should_close:
            conn.close()


def get_calibration_target(
    target_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[CalibrationTargetRecord]:
    """Fetches optical calibration target details."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM optical_calibration_targets WHERE target_id = ?;", (target_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return CalibrationTargetRecord(
            target_id=row["target_id"],
            color_card_standard=row["color_card_standard"],
            reference_l=row["reference_l"],
            reference_a=row["reference_a"],
            reference_b=row["reference_b"],
            tolerance_delta_e=row["tolerance_delta_e"],
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def analyze_optical_image(
    req: OpticalInferenceRequest,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> OpticalInferenceResult:
    """Executes CIELAB color normalization, feature extraction, and Ayurvedic clinical interpretation."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        seed_default_calibration_targets(conn)

        calibrated_l = req.raw_cielab_l
        calibrated_a = req.raw_cielab_a
        calibrated_b = req.raw_cielab_b
        delta_e_shift = 0.0

        if req.calibration_target_id:
            target = get_calibration_target(req.calibration_target_id, conn=conn)
            if target:
                delta_e_shift = compute_cielab_delta_e(
                    req.raw_cielab_l, req.raw_cielab_a, req.raw_cielab_b,
                    target.reference_l, target.reference_a, target.reference_b
                )
                # Apply balanced linear calibration bias
                l_bias = target.reference_l - 50.0
                a_bias = target.reference_a - 0.0
                b_bias = target.reference_b - 0.0
                calibrated_l = round(max(0.0, min(100.0, req.raw_cielab_l - l_bias * 0.1)), 2)
                calibrated_a = round(max(-128.0, min(127.0, req.raw_cielab_a - a_bias * 0.1)), 2)
                calibrated_b = round(max(-128.0, min(127.0, req.raw_cielab_b - b_bias * 0.1)), 2)

        icterus_idx: Optional[float] = None
        coating_pct = float(req.coating_coverage_pct or 0.0)

        # Ayurvedic Clinical Diagnostics Interpretation
        if req.anatomical_target == AnatomicalTarget.JIHWA_TONGUE:
            if coating_pct >= 35.0:
                interpretation = f"Sama Jihwa (Ama involvement indicated by {coating_pct:.1f}% coating coverage; Agnimandya)"
            elif calibrated_a >= 25.0 or (calibrated_b >= 20.0 and coating_pct >= 15.0):
                interpretation = "Paittika Jihwa / Raktadhika (Erythematous lingual mucosa, aggravated Pitta/Rakta dosha)"
            elif calibrated_l <= 45.0 and calibrated_a <= 12.0:
                interpretation = "Vataja Jihwa (Dry, darkened mucosa with micro-fissuring tendencies; Vata aggravation)"
            else:
                interpretation = "Nirama Swastha Jihwa (Physiological pink lingual mucosa with balanced Agni)"

        elif req.anatomical_target == AnatomicalTarget.NETRA_SCLERA_EYE:
            # Icterus corresponds to elevated yellow (b*) in sclera
            icterus_idx = round(max(0.0, (calibrated_b - 4.0) * 3.0), 2)
            if icterus_idx >= 15.0:
                interpretation = f"Netra Peetata / Haridra Netra (Significant scleral icterus index {icterus_idx}; Kamala / Yakrit Vikara)"
            elif calibrated_l >= 75.0 and calibrated_a <= 8.0:
                interpretation = "Netra Panduta (Marked conjunctival/scleral pallor; Pandu Roga / Anemia indication)"
            else:
                interpretation = f"Swastha Netra (Physiological scleral chromaticity, icterus index {icterus_idx})"

        else:  # NAKHA_NAIL
            if calibrated_a <= 8.0:
                interpretation = "Nakha Panduta (Nail bed pallor; Rakta Dhatu depletion)"
            else:
                interpretation = "Swastha Nakha (Normal pink capillary perfusion of nail plate)"

        inference_id = f"inf-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO vision_inference_records (
                inference_id, patient_id, hospital_id, anatomical_target,
                raw_image_hash, calibrated_cielab_l, calibrated_cielab_a,
                calibrated_cielab_b, coating_thickness_pct, icterus_index,
                clinical_interpretation, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                inference_id,
                req.patient_id,
                req.hospital_id,
                req.anatomical_target.value,
                req.image_base64_or_bytes_hash,
                calibrated_l,
                calibrated_a,
                calibrated_b,
                coating_pct,
                icterus_idx,
                interpretation,
                now,
            )
        )

        user_id = current_user.user_id if current_user else "SYSTEM"
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "OPTICAL_INFERENCE",
            "VISION_RECORD",
            inference_id,
            {
                "patient_id": req.patient_id,
                "target": req.anatomical_target.value,
                "coating_pct": coating_pct,
                "icterus_idx": icterus_idx
            }
        )
        conn.commit()

        return OpticalInferenceResult(
            inference_id=inference_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            anatomical_target=req.anatomical_target,
            raw_image_hash=req.image_base64_or_bytes_hash,
            calibrated_cielab_l=calibrated_l,
            calibrated_cielab_a=calibrated_a,
            calibrated_cielab_b=calibrated_b,
            coating_thickness_pct=coating_pct,
            icterus_index=icterus_idx,
            delta_e_calibration_shift=delta_e_shift,
            clinical_interpretation=interpretation,
            analyzed_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_patient_vision_inferences(
    patient_id: str,
    limit: int = 20,
    conn: Optional[sqlite3.Connection] = None
) -> List[OpticalInferenceResult]:
    """Fetches optical inference records for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM vision_inference_records
            WHERE patient_id = ?
            ORDER BY analyzed_at DESC
            LIMIT ?;
            """,
            (patient_id, limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append(
                OpticalInferenceResult(
                    inference_id=r["inference_id"],
                    patient_id=r["patient_id"],
                    hospital_id=r["hospital_id"],
                    anatomical_target=AnatomicalTarget(r["anatomical_target"]),
                    raw_image_hash=r["raw_image_hash"],
                    calibrated_cielab_l=r["calibrated_cielab_l"],
                    calibrated_cielab_a=r["calibrated_cielab_a"],
                    calibrated_cielab_b=r["calibrated_cielab_b"],
                    coating_thickness_pct=r["coating_thickness_pct"],
                    icterus_index=r["icterus_index"],
                    delta_e_calibration_shift=0.0,
                    clinical_interpretation=r["clinical_interpretation"],
                    analyzed_at=r["analyzed_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()
