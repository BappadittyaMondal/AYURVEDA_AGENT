"""
API Endpoints for Sattvavajaya Chikitsa, Manasa Roga & Mental Health CDSS.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.manasa_roga import (
    create_sattvavajaya_prescription,
    get_disorder_profile,
    initialize_manasa_roga_tables,
    list_all_disorders,
    perform_manasa_assessment,
)
from models.manasa_roga import (
    CrisisRiskLevel,
    ManasaAssessmentCreateRequest,
    ManasaAssessmentResponse,
    ManasaDisorderCode,
    ManasaDisorderProfile,
    MentalFacultyScores,
    SattvavajayaPrescriptionCreateRequest,
    SattvavajayaPrescriptionResponse,
    TrigunaVector,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/manasa-roga", tags=["Sattvavajaya Chikitsa & Manasa Roga Mental Health CDSS"])


@router.get("/disorders", response_model=List[ManasaDisorderProfile])
def list_disorders(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[ManasaDisorderProfile]:
    """List all classical Manasa Roga psychiatric disorders with ICD-11 dual codes."""
    return list_all_disorders(conn)


@router.get("/disorders/{disorder_code}", response_model=ManasaDisorderProfile)
def get_disorder_detail(
    disorder_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ManasaDisorderProfile:
    """Retrieve complete clinical, Doshic, and Medhya Rasayana profile of a psychiatric condition."""
    try:
        return get_disorder_profile(disorder_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/assessments", response_model=ManasaAssessmentResponse, status_code=status.HTTP_201_CREATED)
def conduct_manasa_assessment(
    request: ManasaAssessmentCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ManasaAssessmentResponse:
    """
    Perform psychometric Triguna evaluation, compute Prajnaparadha Index (PPI),
    and execute psychiatric emergency crisis triage.
    """
    initialize_manasa_roga_tables(conn)
    try:
        return perform_manasa_assessment(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=422, detail=f"[{e.error_code}] {e.message}")


@router.get("/assessments/patient/{patient_id}", response_model=List[ManasaAssessmentResponse])
def get_patient_assessments(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[ManasaAssessmentResponse]:
    """Retrieve longitudinal psychiatric assessments for a patient."""
    initialize_manasa_roga_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM patient_manasa_assessments
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    results: List[ManasaAssessmentResponse] = []
    for r in rows:
        results.append(
            ManasaAssessmentResponse(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                triguna=TrigunaVector(
                    sattva=r["triguna_sattva"],
                    rajas=r["triguna_rajas"],
                    tamas=r["triguna_tamas"]
                ),
                faculties=MentalFacultyScores(
                    dhi_score=r["dhi_score"],
                    dhriti_score=r["dhriti_score"],
                    smriti_score=r["smriti_score"]
                ),
                prajnaparadha_index=r["prajnaparadha_index"],
                primary_manasa_disorder=ManasaDisorderCode(r["primary_manasa_disorder"]),
                crisis_risk_level=CrisisRiskLevel(r["crisis_risk_level"]),
                clinical_summary=r["clinical_summary"],
                assessed_by_arn="SYSTEM_RMP",
                created_at=r["created_at"],
            )
        )
    return results


@router.post("/prescriptions", response_model=SattvavajayaPrescriptionResponse, status_code=status.HTTP_201_CREATED)
def prescribe_sattvavajaya(
    request: SattvavajayaPrescriptionCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SattvavajayaPrescriptionResponse:
    """
    Formulate integrated Trividha Chikitsa prescription combining Daivavyapashraya,
    Yuktivyapashraya Medhya Rasayanas, and Sattvavajaya Mano-nigraha.
    """
    initialize_manasa_roga_tables(conn)
    try:
        return create_sattvavajaya_prescription(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=422, detail=f"[{e.error_code}] {e.message}")
