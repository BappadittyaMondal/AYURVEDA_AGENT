"""API Endpoints for Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels)."""
import json
import sqlite3
import time
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.security import ClinicalAction
from core.srotas import MULA_STHANA_REGISTRY, evaluate_srotas_matrix
from models.schemas import UserResponse
from models.srotas import (
    ChannelDetail,
    DushtiType,
    SrotasInput,
    SrotasOutput,
    SrotasType,
    SrotoshodhanaDirective,
)

router = APIRouter(prefix="/srotas", tags=["Srotas Pathology & Khavaigunya Engine"])


@router.get("/reference", response_model=List[Dict[str, str | List[str]]])
def get_srotas_reference(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, str | List[str]]]:
    """Retrieve the classical 14 Srotamsi registry with anatomical root origins (Mula Sthana)."""
    return [
        {"srotas": s.value, "mula_sthana": MULA_STHANA_REGISTRY.get(s, [])}
        for s in SrotasType
    ]


@router.post("/evaluate", response_model=SrotasOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_srotas_matrix(
    eval_input: SrotasInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SrotasOutput:
    """Evaluate channel involvement, identify dominant Srotodushti, map Khavaigunya, and generate Srotoshodhana protocols."""
    cursor = conn.cursor()

    # Validate patient exists in current hospital
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (eval_input.patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{eval_input.patient_id}' not found in current hospital tenant",
        )

    evaluator_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    output = evaluate_srotas_matrix(
        input_data=eval_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    details_json = json.dumps([d.model_dump() for d in output.channel_details])
    directives_json = json.dumps([d.model_dump() for d in output.srotoshodhana_directives])

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO srotas_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                overall_srotas_index, vulnerable_channels_count, channel_details_json,
                khavaigunya_channels_json, srotoshodhana_directives_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.assessment_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.overall_srotas_index,
                output.vulnerable_channels_count,
                details_json,
                json.dumps(output.khavaigunya_channels),
                directives_json,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_SROTAS_MATRIX",
            entity_type="srotas_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "overall_srotas_index": output.overall_srotas_index,
                "vulnerable_channels_count": output.vulnerable_channels_count,
                "khavaigunya_channels": output.khavaigunya_channels,
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


@router.get("/patients/{patient_id}/latest", response_model=SrotasOutput)
def get_latest_srotas_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SrotasOutput:
    """Retrieve the most recent Srotas pathology assessment for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               overall_srotas_index, vulnerable_channels_count, channel_details_json,
               khavaigunya_channels_json, srotoshodhana_directives_json, timestamp
        FROM srotas_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Srotas assessments recorded for patient '{patient_id}'",
        )

    details_raw = json.loads(row["channel_details_json"])
    directives_raw = json.loads(row["srotoshodhana_directives_json"])

    details = [ChannelDetail(**d) for d in details_raw]
    directives = [SrotoshodhanaDirective(**d) for d in directives_raw]

    return SrotasOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        overall_srotas_index=row["overall_srotas_index"],
        vulnerable_channels_count=row["vulnerable_channels_count"],
        channel_details=details,
        khavaigunya_channels=json.loads(row["khavaigunya_channels_json"]),
        srotoshodhana_directives=directives,
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[SrotasOutput])
def get_srotas_assessment_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SrotasOutput]:
    """Retrieve full chronological history of Srotas pathology assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               overall_srotas_index, vulnerable_channels_count, channel_details_json,
               khavaigunya_channels_json, srotoshodhana_directives_json, timestamp
        FROM srotas_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    results = []
    for r in rows:
        details_raw = json.loads(r["channel_details_json"])
        directives_raw = json.loads(r["srotoshodhana_directives_json"])

        details = [ChannelDetail(**d) for d in details_raw]
        directives = [SrotoshodhanaDirective(**d) for d in directives_raw]

        results.append(
            SrotasOutput(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                evaluator_arn=r["evaluator_arn"],
                overall_srotas_index=r["overall_srotas_index"],
                vulnerable_channels_count=r["vulnerable_channels_count"],
                channel_details=details,
                khavaigunya_channels=json.loads(r["khavaigunya_channels_json"]),
                srotoshodhana_directives=directives,
                timestamp=r["timestamp"],
            )
        )
    return results
