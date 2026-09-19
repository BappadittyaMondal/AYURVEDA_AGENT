"""API Endpoints for Jihwa Pariksha Computer Vision & Micro-Colorimetry Tongue Coating Analysis."""
import json
import sqlite3
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.jihwa_cv import evaluate_jihwa, simulate_jihwa
from core.security import ClinicalAction
from models.jihwa import (
    CoatingThickness,
    DominantColor,
    JihwaInput,
    JihwaOutput,
    JihwaSimulationRequest,
    JihwaSimulationResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/jihwa", tags=["Jihwa Pariksha Computer Vision"])


@router.post("/evaluate", response_model=JihwaOutput, status_code=status.HTTP_201_CREATED)
def evaluate_tongue_coating(
    jihwa_input: JihwaInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> JihwaOutput:
    """Evaluate lingual colorimetry, coating ratio, fissure density, Doshic vector, and Ama index."""
    cursor = conn.cursor()

    # Validate patient exists in current hospital
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (jihwa_input.patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{jihwa_input.patient_id}' not found in current hospital tenant",
        )

    examiner_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    output = evaluate_jihwa(
        data=jihwa_input,
        examiner_arn=examiner_arn,
        hospital_id=current_user.hospital_id,
    )

    findings_payload = {
        "findings_summary": output.findings_summary,
        "somatotopic_mapping": output.somatotopic_mapping,
    }

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO jihwa_examinations (
                exam_id, patient_id, hospital_id, examiner_arn, image_hash,
                coating_ratio, coating_thickness, dominant_color, fissure_density,
                cie_l, cie_a, cie_b, ama_score, vata_score, pitta_score, kapha_score,
                primary_dosha, is_sama, findings_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.exam_id,
                output.patient_id,
                output.hospital_id,
                output.examiner_arn,
                output.image_hash,
                output.coating_ratio,
                output.coating_thickness.value,
                output.dominant_color.value,
                output.fissure_density,
                output.cie_l,
                output.cie_a,
                output.cie_b,
                output.ama_score,
                output.vata_score,
                output.pitta_score,
                output.kapha_score,
                output.primary_dosha,
                1 if output.is_sama else 0,
                json.dumps(findings_payload),
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_JIHWA_PARIKSHA",
            entity_type="jihwa_examination",
            entity_id=output.exam_id,
            details={
                "patient_id": output.patient_id,
                "primary_dosha": output.primary_dosha,
                "ama_score": output.ama_score,
                "dominant_color": output.dominant_color.value,
            },
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failure: {str(e)}",
        )

    return output


@router.post("/simulate", response_model=JihwaSimulationResponse)
def simulate_tongue_parameters(
    sim_request: JihwaSimulationRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> JihwaSimulationResponse:
    """Synthesize calibrated lingual parameters and colorimetry for testing and simulation."""
    return simulate_jihwa(target_condition=sim_request.target_condition)


@router.get("/patients/{patient_id}/latest", response_model=JihwaOutput)
def get_latest_jihwa_exam(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> JihwaOutput:
    """Retrieve the most recent Jihwa Pariksha examination for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT exam_id, patient_id, hospital_id, examiner_arn, image_hash,
               coating_ratio, coating_thickness, dominant_color, fissure_density,
               cie_l, cie_a, cie_b, ama_score, vata_score, pitta_score, kapha_score,
               primary_dosha, is_sama, findings_json, timestamp
        FROM jihwa_examinations
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Jihwa examinations recorded for patient '{patient_id}'",
        )

    findings_data = json.loads(row["findings_json"])

    return JihwaOutput(
        exam_id=row["exam_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        examiner_arn=row["examiner_arn"],
        image_hash=row["image_hash"],
        coating_ratio=row["coating_ratio"],
        coating_thickness=CoatingThickness(row["coating_thickness"]),
        dominant_color=DominantColor(row["dominant_color"]),
        fissure_density=row["fissure_density"],
        cie_l=row["cie_l"],
        cie_a=row["cie_a"],
        cie_b=row["cie_b"],
        ama_score=row["ama_score"],
        vata_score=row["vata_score"],
        pitta_score=row["pitta_score"],
        kapha_score=row["kapha_score"],
        primary_dosha=row["primary_dosha"],
        is_sama=bool(row["is_sama"]),
        findings_summary=findings_data.get("findings_summary", ""),
        somatotopic_mapping=findings_data.get("somatotopic_mapping", {}),
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[JihwaOutput])
def get_jihwa_exam_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[JihwaOutput]:
    """Retrieve full chronological history of Jihwa Pariksha examinations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT exam_id, patient_id, hospital_id, examiner_arn, image_hash,
               coating_ratio, coating_thickness, dominant_color, fissure_density,
               cie_l, cie_a, cie_b, ama_score, vata_score, pitta_score, kapha_score,
               primary_dosha, is_sama, findings_json, timestamp
        FROM jihwa_examinations
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    outputs = []
    for r in rows:
        f_data = json.loads(r["findings_json"])
        outputs.append(
            JihwaOutput(
                exam_id=r["exam_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                examiner_arn=r["examiner_arn"],
                image_hash=r["image_hash"],
                coating_ratio=r["coating_ratio"],
                coating_thickness=CoatingThickness(r["coating_thickness"]),
                dominant_color=DominantColor(r["dominant_color"]),
                fissure_density=r["fissure_density"],
                cie_l=r["cie_l"],
                cie_a=r["cie_a"],
                cie_b=r["cie_b"],
                ama_score=r["ama_score"],
                vata_score=r["vata_score"],
                pitta_score=r["pitta_score"],
                kapha_score=r["kapha_score"],
                primary_dosha=r["primary_dosha"],
                is_sama=bool(r["is_sama"]),
                findings_summary=f_data.get("findings_summary", ""),
                somatotopic_mapping=f_data.get("somatotopic_mapping", {}),
                timestamp=r["timestamp"],
            )
        )
    return outputs
