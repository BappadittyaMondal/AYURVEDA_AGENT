"""
API Endpoints for Classical Disease Classification & Morbidity Dual-Coding (ICD-11 & NAMASTE).
"""

import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.morbidity_coding import (
    get_crosswalk_entry,
    get_patient_diagnoses,
    record_patient_diagnosis,
    search_morbidity_registry,
)
from core.security import ClinicalAction
from models.morbidity_coding import (
    DoshicCategory,
    MorbidityCrosswalkEntry,
    PatientDiagnosisCodingInput,
    PatientDiagnosisCodingOutput,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/morbidity-coding", tags=["Morbidity Dual-Coding & ICD-11 Crosswalk"])


@router.get("/registry", response_model=List[MorbidityCrosswalkEntry])
def list_or_search_registry(
    q: Optional[str] = Query(default=None, description="Search by Sanskrit name, English name, NAMASTE, or ICD code"),
    doshic_category: Optional[DoshicCategory] = Query(default=None, description="Filter by Doshic etiology"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[MorbidityCrosswalkEntry]:
    """Search and browse the classical Ashtodara Shata taxonomy and dual-coding registry."""
    return search_morbidity_registry(conn=conn, query=q, doshic_filter=doshic_category)


@router.get("/registry/{disease_code}", response_model=MorbidityCrosswalkEntry)
def get_registry_entry(
    disease_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MorbidityCrosswalkEntry:
    """Retrieves full dual-coding crosswalk by disease code, NAMASTE code, or ICD-11 code."""
    entry = get_crosswalk_entry(conn, disease_code)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Morbidity entry '{disease_code}' not found in registry",
        )
    return entry


@router.post("/patients/{patient_id}/diagnose", response_model=PatientDiagnosisCodingOutput, status_code=status.HTTP_201_CREATED)
def assign_patient_diagnosis(
    patient_id: str,
    diag_input: PatientDiagnosisCodingInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> PatientDiagnosisCodingOutput:
    """
    Assigns a verified dual-coded diagnosis to a patient, generates an ABDM FHIR Condition,
    and commits to the immutable EHR clinical ledger.
    """
    if diag_input.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path patient_id '{patient_id}' does not match body patient_id '{diag_input.patient_id}'",
        )

    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant",
        )

    diagnosing_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        output = record_patient_diagnosis(
            conn=conn,
            input_data=diag_input,
            diagnosing_arn=diagnosing_arn,
            hospital_id=current_user.hospital_id,
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="RECORD_PATIENT_DIAGNOSIS",
            entity_type="patient_diagnosis_coding",
            entity_id=output.coding_id,
            details={
                "patient_id": patient_id,
                "disease_code": output.disease_crosswalk.disease_code,
                "namaste_code": output.disease_crosswalk.namaste_code,
                "icd11_tm2_code": output.disease_crosswalk.icd11_tm2_code,
                "icd11_biomed_code": output.disease_crosswalk.icd11_biomed_code,
                "verification_status": output.verification_status.value,
            },
        )
        conn.commit()
    except ValueError as ve:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failure: {str(e)}",
        )

    return output


@router.get("/patients/{patient_id}/diagnoses", response_model=List[PatientDiagnosisCodingOutput])
def get_patient_diagnoses_list(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[PatientDiagnosisCodingOutput]:
    """Retrieves all confirmed dual-coded diagnoses recorded for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant",
        )

    return get_patient_diagnoses(conn, patient_id)


@router.get("/patients/{patient_id}/fhir-conditions", response_model=Dict[str, Any])
def get_patient_fhir_conditions_bundle(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Exports all confirmed patient diagnoses as an ABDM / HL7 FHIR R4 Collection Bundle
    for clinical exchange and health record interoperability.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant",
        )

    diagnoses = get_patient_diagnoses(conn, patient_id)

    bundle: Dict[str, Any] = {
        "resourceType": "Bundle",
        "type": "collection",
        "total": len(diagnoses),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{d.fhir_condition.get('id', '')}",
                "resource": d.fhir_condition
            }
            for d in diagnoses
        ]
    }

    return bundle
