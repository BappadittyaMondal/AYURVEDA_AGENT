"""Vikriti Dynamic Differential Analysis & VSI Scoring Router."""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.security import ClinicalAction
from core.vikriti import (
    VIKRITI_SYMPTOMS,
    compute_doshic_deltas,
    compute_kl_divergence,
    compute_mahalanobis_distance,
    compute_vikriti_vector,
    compute_vsi,
)
from models.schemas import UserResponse
from models.vikriti import (
    DoshicDeltaOutput,
    VikritiAssessmentInput,
    VikritiAssessmentOutput,
    VikritiSeverityTier,
)

router = APIRouter(prefix="/vikriti", tags=["Vikriti Dynamic Differential Engine"])


@router.get("/symptoms", response_model=List[Dict[str, Any]])
def get_vikriti_symptoms_list(
    current_user: UserResponse = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Retrieve the 24 standardized acute Doshic presentation symptom indicators."""
    return VIKRITI_SYMPTOMS


@router.post("/patients/{patient_id}", response_model=VikritiAssessmentOutput, status_code=status.HTTP_201_CREATED)
def assess_patient_vikriti(
    patient_id: str,
    assessment_input: VikritiAssessmentInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> VikritiAssessmentOutput:
    """
    Evaluate acute presentation symptoms, compute Doshic divergence vector V_curr,
    calculate KL Divergence, Mahalanobis distance from baseline Prakriti, and assign VSI severity tier.
    """
    cursor = conn.cursor()

    # Verify patient exists and belongs to current hospital tenant
    cursor.execute(
        """
        SELECT patient_id, hospital_id, prakriti_vata, prakriti_pitta, prakriti_kapha
        FROM patients WHERE patient_id = ? AND hospital_id = ?;
        """,
        (patient_id, current_user.hospital_id)
    )
    patient = cursor.fetchone()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant"
        )

    prakriti_v = float(patient["prakriti_vata"])
    prakriti_p = float(patient["prakriti_pitta"])
    prakriti_k = float(patient["prakriti_kapha"])
    prakriti_base = (prakriti_v, prakriti_p, prakriti_k)

    # 1. Compute dynamic Vikriti vector
    vikriti_curr = compute_vikriti_vector(assessment_input.symptoms)

    # 2. Compute divergence metrics
    kl = compute_kl_divergence(vikriti_curr, prakriti_base)
    dm = compute_mahalanobis_distance(vikriti_curr, prakriti_base)

    # 3. Compute VSI and recommendation
    vsi, tier, rec = compute_vsi(kl, dm)

    # 4. Compute directional deltas
    deltas = compute_doshic_deltas(vikriti_curr, prakriti_base)

    assessment_id = f"vik-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    evaluator_arn = current_user.arn or "SYSTEM_EVALUATOR"

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO vikriti_assessments (
                assessment_id, patient_id, hospital_id, evaluated_by_arn,
                vata_v, pitta_v, kapha_v, kl_divergence, mahalanobis_dist,
                vsi_score, severity_tier, deltas_json, answers_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                assessment_id,
                patient_id,
                current_user.hospital_id,
                evaluator_arn,
                vikriti_curr[0],
                vikriti_curr[1],
                vikriti_curr[2],
                kl,
                dm,
                vsi,
                tier.value,
                deltas.model_dump_json(),
                json.dumps(assessment_input.symptoms),
                now
            )
        )

        append_audit_log(
            conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_VIKRITI_DIVERGENCE",
            entity_type="VIKRITI_ASSESSMENT",
            entity_id=assessment_id,
            details={
                "patient_id": patient_id,
                "vsi_score": vsi,
                "severity_tier": tier.value,
                "dominant_vitiation": deltas.dominant_vitiation
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return VikritiAssessmentOutput(
        assessment_id=assessment_id,
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        evaluated_by_arn=evaluator_arn,
        prakriti_baseline={"vata": prakriti_v, "pitta": prakriti_p, "kapha": prakriti_k},
        vikriti_current={"vata": vikriti_curr[0], "pitta": vikriti_curr[1], "kapha": vikriti_curr[2]},
        kl_divergence=kl,
        mahalanobis_distance=dm,
        vsi_score=vsi,
        severity_tier=tier,
        doshic_deltas=deltas,
        clinical_recommendation=rec,
        timestamp=now
    )


@router.get("/patients/{patient_id}/latest", response_model=VikritiAssessmentOutput)
def get_latest_vikriti_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> VikritiAssessmentOutput:
    """Retrieve the most recent Vikriti evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT v.assessment_id, v.patient_id, v.hospital_id, v.evaluated_by_arn,
               v.vata_v, v.pitta_v, v.kapha_v, v.kl_divergence, v.mahalanobis_dist,
               v.vsi_score, v.severity_tier, v.deltas_json, v.timestamp,
               p.prakriti_vata, p.prakriti_pitta, p.prakriti_kapha
        FROM vikriti_assessments v
        JOIN patients p ON v.patient_id = p.patient_id
        WHERE v.patient_id = ? AND v.hospital_id = ?
        ORDER BY v.timestamp DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Vikriti assessments found for patient '{patient_id}'"
        )

    tier = VikritiSeverityTier(row["severity_tier"])
    _, _, rec = compute_vsi(row["kl_divergence"], row["mahalanobis_dist"])
    deltas = DoshicDeltaOutput.model_validate_json(row["deltas_json"])

    return VikritiAssessmentOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluated_by_arn=row["evaluated_by_arn"],
        prakriti_baseline={
            "vata": float(row["prakriti_vata"]),
            "pitta": float(row["prakriti_pitta"]),
            "kapha": float(row["prakriti_kapha"])
        },
        vikriti_current={
            "vata": float(row["vata_v"]),
            "pitta": float(row["pitta_v"]),
            "kapha": float(row["kapha_v"])
        },
        kl_divergence=float(row["kl_divergence"]),
        mahalanobis_distance=float(row["mahalanobis_dist"]),
        vsi_score=float(row["vsi_score"]),
        severity_tier=tier,
        doshic_deltas=deltas,
        clinical_recommendation=rec,
        timestamp=row["timestamp"]
    )


@router.get("/patients/{patient_id}/history", response_model=List[VikritiAssessmentOutput])
def get_vikriti_history(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[VikritiAssessmentOutput]:
    """Retrieve longitudinal Vikriti trajectory for patient progress monitoring."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT v.assessment_id, v.patient_id, v.hospital_id, v.evaluated_by_arn,
               v.vata_v, v.pitta_v, v.kapha_v, v.kl_divergence, v.mahalanobis_dist,
               v.vsi_score, v.severity_tier, v.deltas_json, v.timestamp,
               p.prakriti_vata, p.prakriti_pitta, p.prakriti_kapha
        FROM vikriti_assessments v
        JOIN patients p ON v.patient_id = p.patient_id
        WHERE v.patient_id = ? AND v.hospital_id = ?
        ORDER BY v.timestamp DESC;
        """,
        (patient_id, current_user.hospital_id)
    )
    rows = cursor.fetchall()

    result = []
    for row in rows:
        tier = VikritiSeverityTier(row["severity_tier"])
        _, _, rec = compute_vsi(row["kl_divergence"], row["mahalanobis_dist"])
        deltas = DoshicDeltaOutput.model_validate_json(row["deltas_json"])
        result.append(
            VikritiAssessmentOutput(
                assessment_id=row["assessment_id"],
                patient_id=row["patient_id"],
                hospital_id=row["hospital_id"],
                evaluated_by_arn=row["evaluated_by_arn"],
                prakriti_baseline={
                    "vata": float(row["prakriti_vata"]),
                    "pitta": float(row["prakriti_pitta"]),
                    "kapha": float(row["prakriti_kapha"])
                },
                vikriti_current={
                    "vata": float(row["vata_v"]),
                    "pitta": float(row["pitta_v"]),
                    "kapha": float(row["kapha_v"])
                },
                kl_divergence=float(row["kl_divergence"]),
                mahalanobis_distance=float(row["mahalanobis_dist"]),
                vsi_score=float(row["vsi_score"]),
                severity_tier=tier,
                doshic_deltas=deltas,
                clinical_recommendation=rec,
                timestamp=row["timestamp"]
            )
        )
    return result
