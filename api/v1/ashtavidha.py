"""Ashtavidha Pariksha (8-Fold Clinical Examination) Router."""
import json
import sqlite3
import time
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.ashtavidha import evaluate_ashtavidha_pariksha
from core.database import append_audit_log
from core.security import ClinicalAction
from models.ashtavidha import AshtavidhaParikshaInput, AshtavidhaParikshaOutput
from models.schemas import UserResponse

router = APIRouter(prefix="/ashtavidha", tags=["Ashtavidha Pariksha Diagnostic Engine"])


@router.post("/patients/{patient_id}", response_model=AshtavidhaParikshaOutput, status_code=status.HTTP_201_CREATED)
def record_ashtavidha_examination(
    patient_id: str,
    exam_input: AshtavidhaParikshaInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> AshtavidhaParikshaOutput:
    """
    Record an 8-fold clinical examination (Nadi, Mutra, Mala, Jihwa, Shabda, Sparsha, Drik, Akriti),
    compute Doshic manifestations, and detect Ama presence.
    """
    cursor = conn.cursor()

    cursor.execute(
        "SELECT patient_id, hospital_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id)
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant"
        )

    v, p, k, primary, secondary, ama, summary = evaluate_ashtavidha_pariksha(exam_input)

    exam_id = f"ash-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    examiner_arn = current_user.arn or "EXAMINER_ARN_PENDING"

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO ashtavidha_examinations (
                exam_id, patient_id, hospital_id, examiner_arn,
                nadi_json, mutra_json, mala_json, jihwa_json, shabda_json, sparsha_json, drik_json, akriti_json,
                vata_score, pitta_score, kapha_score, primary_dosha, secondary_dosha, ama_suspected, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                exam_id,
                patient_id,
                current_user.hospital_id,
                examiner_arn,
                exam_input.nadi.model_dump_json(),
                exam_input.mutra.model_dump_json(),
                exam_input.mala.model_dump_json(),
                exam_input.jihwa.model_dump_json(),
                exam_input.shabda.model_dump_json(),
                exam_input.sparsha.model_dump_json(),
                exam_input.drik.model_dump_json(),
                exam_input.akriti.model_dump_json(),
                v, p, k, primary, secondary, 1 if ama else 0, now
            )
        )

        append_audit_log(
            conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="RECORD_ASHTAVIDHA_EXAM",
            entity_type="ASHTAVIDHA_EXAMINATION",
            entity_id=exam_id,
            details={
                "patient_id": patient_id,
                "primary_dosha": primary,
                "secondary_dosha": secondary,
                "ama_suspected": ama
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return AshtavidhaParikshaOutput(
        exam_id=exam_id,
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        examiner_arn=examiner_arn,
        vata_score=v,
        pitta_score=p,
        kapha_score=k,
        primary_dosha=primary,
        secondary_dosha=secondary,
        ama_suspected=ama,
        summary_findings=summary,
        timestamp=now
    )


@router.get("/patients/{patient_id}/latest", response_model=AshtavidhaParikshaOutput)
def get_latest_ashtavidha_examination(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> AshtavidhaParikshaOutput:
    """Retrieve the most recent Ashtavidha Pariksha evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT exam_id, patient_id, hospital_id, examiner_arn,
               vata_score, pitta_score, kapha_score, primary_dosha, secondary_dosha,
               ama_suspected, timestamp
        FROM ashtavidha_examinations
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Ashtavidha Pariksha records found for patient '{patient_id}'"
        )

    return AshtavidhaParikshaOutput(
        exam_id=row["exam_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        examiner_arn=row["examiner_arn"],
        vata_score=float(row["vata_score"]),
        pitta_score=float(row["pitta_score"]),
        kapha_score=float(row["kapha_score"]),
        primary_dosha=row["primary_dosha"],
        secondary_dosha=row["secondary_dosha"],
        ama_suspected=bool(row["ama_suspected"]),
        summary_findings=f"Primary {row['primary_dosha']} presentation recorded.",
        timestamp=row["timestamp"]
    )


@router.get("/patients/{patient_id}/history", response_model=List[AshtavidhaParikshaOutput])
def get_ashtavidha_history(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[AshtavidhaParikshaOutput]:
    """Retrieve historical progression of Ashtavidha Pariksha records for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT exam_id, patient_id, hospital_id, examiner_arn,
               vata_score, pitta_score, kapha_score, primary_dosha, secondary_dosha,
               ama_suspected, timestamp
        FROM ashtavidha_examinations
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC;
        """,
        (patient_id, current_user.hospital_id)
    )
    rows = cursor.fetchall()
    return [
        AshtavidhaParikshaOutput(
            exam_id=r["exam_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            examiner_arn=r["examiner_arn"],
            vata_score=float(r["vata_score"]),
            pitta_score=float(r["pitta_score"]),
            kapha_score=float(r["kapha_score"]),
            primary_dosha=r["primary_dosha"],
            secondary_dosha=r["secondary_dosha"],
            ama_suspected=bool(r["ama_suspected"]),
            summary_findings=f"Recorded {r['primary_dosha']} presentation.",
            timestamp=r["timestamp"]
        )
        for r in rows
    ]
