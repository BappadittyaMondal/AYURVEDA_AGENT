"""API Endpoints for Taila Bindu Pariksha Diagnostic & Surface-Tension Fluid Dynamics."""
import json
import sqlite3
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.security import ClinicalAction
from core.taila_bindu import evaluate_taila_bindu, simulate_taila_bindu
from models.schemas import UserResponse
from models.taila_bindu import (
    TailaBinduInput,
    TailaBinduOutput,
    TailaBinduSimulationRequest,
    TailaBinduSimulationResponse,
    CompassDirection,
    DoshicShape,
    PrognosisVerdict,
)

router = APIRouter(prefix="/taila-bindu", tags=["Taila Bindu Pariksha Fluid Dynamics"])


@router.post("/evaluate", response_model=TailaBinduOutput, status_code=status.HTTP_201_CREATED)
def evaluate_droplet_test(
    droplet_input: TailaBinduInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> TailaBinduOutput:
    """Evaluate oil droplet spreading mechanics, shape morphology, and classical prognosis."""
    cursor = conn.cursor()

    # Validate patient exists in current hospital
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (droplet_input.patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{droplet_input.patient_id}' not found in current hospital tenant",
        )

    evaluator_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    output = evaluate_taila_bindu(
        data=droplet_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO taila_bindu_sessions (
                session_id, patient_id, hospital_id, evaluator_arn,
                urine_temp, surface_tension, spreading_coeff, spreading_velocity,
                eccentricity, circularity, direction, fragment_count,
                submerged, doshic_shape, prognosis_verdict, commentary, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.session_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.urine_temp,
                output.surface_tension,
                output.spreading_coeff,
                output.spreading_velocity,
                output.eccentricity,
                output.circularity,
                output.direction.value,
                output.fragment_count,
                1 if output.submerged else 0,
                output.doshic_shape.value,
                output.prognosis_verdict.value,
                output.commentary,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_TAILA_BINDU",
            entity_type="taila_bindu_session",
            entity_id=output.session_id,
            details={
                "patient_id": output.patient_id,
                "doshic_shape": output.doshic_shape.value,
                "prognosis_verdict": output.prognosis_verdict.value,
                "spreading_coeff": output.spreading_coeff,
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


@router.post("/simulate", response_model=TailaBinduSimulationResponse)
def simulate_droplet_parameters(
    sim_request: TailaBinduSimulationRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> TailaBinduSimulationResponse:
    """Synthesize classical fluid dynamic parameters for simulated conditions."""
    return simulate_taila_bindu(
        doshic_condition=sim_request.doshic_condition,
        urine_temp=sim_request.urine_temp,
        drop_height_angula=sim_request.drop_height_angula,
    )


@router.get("/patients/{patient_id}/latest", response_model=TailaBinduOutput)
def get_latest_taila_bindu(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> TailaBinduOutput:
    """Retrieve the most recent Taila Bindu Pariksha session for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, patient_id, hospital_id, evaluator_arn,
               urine_temp, surface_tension, spreading_coeff, spreading_velocity,
               eccentricity, circularity, direction, fragment_count,
               submerged, doshic_shape, prognosis_verdict, commentary, timestamp
        FROM taila_bindu_sessions
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Taila Bindu sessions recorded for patient '{patient_id}'",
        )

    return TailaBinduOutput(
        session_id=row["session_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        urine_temp=row["urine_temp"],
        surface_tension=row["surface_tension"],
        spreading_coeff=row["spreading_coeff"],
        spreading_velocity=row["spreading_velocity"],
        eccentricity=row["eccentricity"],
        circularity=row["circularity"],
        direction=CompassDirection(row["direction"]),
        fragment_count=row["fragment_count"],
        submerged=bool(row["submerged"]),
        doshic_shape=DoshicShape(row["doshic_shape"]),
        prognosis_verdict=PrognosisVerdict(row["prognosis_verdict"]),
        commentary=row["commentary"],
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[TailaBinduOutput])
def get_taila_bindu_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[TailaBinduOutput]:
    """Retrieve full chronological history of Taila Bindu examinations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, patient_id, hospital_id, evaluator_arn,
               urine_temp, surface_tension, spreading_coeff, spreading_velocity,
               eccentricity, circularity, direction, fragment_count,
               submerged, doshic_shape, prognosis_verdict, commentary, timestamp
        FROM taila_bindu_sessions
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()
    return [
        TailaBinduOutput(
            session_id=r["session_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            evaluator_arn=r["evaluator_arn"],
            urine_temp=r["urine_temp"],
            surface_tension=r["surface_tension"],
            spreading_coeff=r["spreading_coeff"],
            spreading_velocity=r["spreading_velocity"],
            eccentricity=r["eccentricity"],
            circularity=r["circularity"],
            direction=CompassDirection(r["direction"]),
            fragment_count=r["fragment_count"],
            submerged=bool(r["submerged"]),
            doshic_shape=DoshicShape(r["doshic_shape"]),
            prognosis_verdict=PrognosisVerdict(r["prognosis_verdict"]),
            commentary=r["commentary"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]
