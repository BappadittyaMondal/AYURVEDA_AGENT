"""
api/v1/ayush_grid.py - API Endpoints for Phase 42: AYUSH GRID Bridge & Zero-Knowledge Verification.
"""

import sqlite3
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.ayush_grid import (
    FhirBundleDispatchReq,
    FhirBundleRecord,
    ZkProofGenerateReq,
    ZkProofRecord,
    ZkProofVerifyReq,
)
from core.ayush_grid import (
    dispatch_fhir_bundle_to_ayush_grid,
    generate_zero_knowledge_proof,
    verify_zero_knowledge_proof,
    get_patient_ayush_grid_logs,
)

router = APIRouter(prefix="/ayush-grid", tags=["Phase 42: AYUSH GRID Bridge & Zero-Knowledge Verification"])


@router.post(
    "/dispatch",
    response_model=FhirBundleRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch ABDM FHIR R4 document bundle to AYUSH GRID gateway"
)
def dispatch_bundle_endpoint(
    req: FhirBundleDispatchReq,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return dispatch_fhir_bundle_to_ayush_grid(req, current_user=current_user, conn=conn)


@router.get(
    "/patient/{patient_id}/logs",
    response_model=List[FhirBundleRecord],
    summary="Get ABDM dispatch logs for a patient"
)
def get_patient_logs_endpoint(
    patient_id: str,
    limit: int = 10,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_ayush_grid_logs(patient_id, limit=limit, conn=conn)


@router.post(
    "/zkp/generate",
    response_model=ZkProofRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate zero-knowledge cryptographic commitment proof"
)
def generate_zkp_endpoint(
    req: ZkProofGenerateReq,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return generate_zero_knowledge_proof(req, current_user=current_user, conn=conn)


@router.post(
    "/zkp/verify",
    response_model=Dict[str, Any],
    summary="Verify a zero-knowledge commitment proof"
)
def verify_zkp_endpoint(
    req: ZkProofVerifyReq,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    is_valid = verify_zero_knowledge_proof(req, conn=conn)
    return {
        "proof_id": req.proof_id,
        "is_valid": is_valid,
        "status": "VERIFIED_VALID" if is_valid else "INVALID_PROOF"
    }
