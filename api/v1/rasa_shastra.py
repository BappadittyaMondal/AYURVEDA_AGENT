"""
API Endpoints for Rasa Shastra & Herbo-Mineral Processing Safety.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    HeavyMetalExposureExceededException,
    RecordNotFoundException,
    ScheduleE1ShodhanaMissingException,
)
from core.rasa_shastra import (
    certify_bhasma_batch_release,
    check_schedule_e1_shodhana_compliance,
    evaluate_heavy_metal_exposure,
    get_mineral_profile,
    initialize_rasa_shastra_tables,
    verify_shodhana_batch,
)
from models.rasa_shastra import (
    BhasmaBatchReleaseCertificate,
    BhasmaBatchReleaseRequest,
    BhasmaPariksha,
    ElementalAssay,
    HeavyMetalExposureCheckRequest,
    HeavyMetalExposureCheckResponse,
    ParticleSizeAnalysis,
    PutaType,
    RasaCategory,
    RasaMineralRecord,
    ShodhanaMethod,
    ShodhanaRecord,
    ShodhanaVerificationRequest,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/rasashastra", tags=["Rasa Shastra & Herbo-Mineral Safety Engine"])


@router.get("/minerals", response_model=List[RasaMineralRecord])
def list_or_search_minerals(
    q: Optional[str] = Query(default=None, description="Search by mineral/substance name or chemical formula"),
    category: Optional[RasaCategory] = Query(default=None, description="Filter by Rasashastra category"),
    schedule_e1_only: bool = Query(default=False, description="Filter for statutory Schedule E(1) poisonous substances"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[RasaMineralRecord]:
    """Search and browse classical minerals, metals, and Schedule E(1) poisons."""
    initialize_rasa_shastra_tables(conn)
    cursor = conn.cursor()

    query = "SELECT * FROM rasa_minerals_registry WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category.value)

    if schedule_e1_only:
        query += " AND is_schedule_e1_poison = 1"

    cursor.execute(query + " ORDER BY mineral_id ASC;", params)
    rows = cursor.fetchall()

    results: List[RasaMineralRecord] = []
    for r in rows:
        rec = RasaMineralRecord(
            mineral_id=r["mineral_id"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            chemical_formula=r["chemical_formula"],
            category=RasaCategory(r["category"]),
            is_schedule_e1_poison=bool(r["is_schedule_e1_poison"]),
            shodhana_required=bool(r["shodhana_required"]),
            standard_shodhana_method=ShodhanaMethod(r["standard_shodhana_method"]),
            standard_shodhana_media=json.loads(r["standard_shodhana_media_json"]),
            minimum_shodhana_cycles=r["minimum_shodhana_cycles"],
            standard_puta_type=PutaType(r["standard_puta_type"]) if r["standard_puta_type"] else None,
            minimum_puta_cycles=r["minimum_puta_cycles"],
            therapeutic_dose_mg_min=r["therapeutic_dose_mg_min"],
            therapeutic_dose_mg_max=r["therapeutic_dose_mg_max"],
            classical_indications=json.loads(r["classical_indications_json"]),
            toxicity_risk_profile=r["toxicity_risk_profile"],
        )
        if q:
            term = q.lower()
            if (
                term in rec.sanskrit_name.lower()
                or term in rec.english_name.lower()
                or term in rec.chemical_formula.lower()
                or any(term in ind.lower() for ind in rec.classical_indications)
            ):
                results.append(rec)
        else:
            results.append(rec)

    return results


@router.get("/minerals/{mineral_id}", response_model=RasaMineralRecord)
def get_mineral_detail(
    mineral_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> RasaMineralRecord:
    """Retrieve full classical profile, purification method, and safety requirements for a mineral."""
    try:
        return get_mineral_profile(mineral_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/shodhana/verify", response_model=ShodhanaRecord)
def submit_shodhana_verification(
    request: ShodhanaVerificationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ShodhanaRecord:
    """Certify and persist raw material Shodhana detoxification."""
    try:
        return verify_shodhana_batch(request, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/shodhana/check-compliance/{mineral_id}")
def check_shodhana_compliance(
    mineral_id: str,
    batch_id: Optional[str] = Query(default=None, description="Batch lot number if verifying specific lot"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
):
    """Verify statutory Shodhana compliance prior to processing Schedule E(1) poisons or metals."""
    try:
        is_compliant = check_schedule_e1_shodhana_compliance(mineral_id, batch_id, conn)
        return {
            "mineral_id": mineral_id,
            "batch_id": batch_id,
            "is_shodhana_compliant": is_compliant,
            "status": "APPROVED_FOR_PROCESSING_OR_DISPENSING"
        }
    except ScheduleE1ShodhanaMissingException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/bhasma/batch-release", response_model=BhasmaBatchReleaseCertificate)
def release_bhasma_batch(
    request: BhasmaBatchReleaseRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> BhasmaBatchReleaseCertificate:
    """
    Perform full laboratory and classical quality control release audit for a Bhasma batch.
    Validates 7-Pariksha criteria, Puta adequacy, AAS/ICP-MS heavy metals, and Particle Size.
    """
    try:
        return certify_bhasma_batch_release(request, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/bhasma/batches/{batch_id}", response_model=BhasmaBatchReleaseCertificate)
def get_bhasma_batch_certificate(
    batch_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> BhasmaBatchReleaseCertificate:
    """Retrieve full batch analytical release certificate."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bhasma_batches WHERE batch_id = ?;", (batch_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bhasma batch '{batch_id}' not found")

    return BhasmaBatchReleaseCertificate(
        batch_id=row["batch_id"],
        mineral_id=row["mineral_id"],
        formulation_name=row["formulation_name"],
        puta_type=PutaType(row["puta_type"]),
        putas_completed=row["putas_completed"],
        classical_pariksha=BhasmaPariksha(**json.loads(row["classical_pariksha_json"])),
        elemental_assay=ElementalAssay(**json.loads(row["elemental_assay_json"])),
        particle_size=ParticleSizeAnalysis(**json.loads(row["particle_size_json"])),
        is_classical_certified=bool(row["is_classical_certified"]),
        puta_count_adequate=True if row["putas_completed"] >= 7 else False,  # general check
        heavy_metals_safe=bool(row["is_physicochemical_certified"]),
        particle_size_compliant=bool(row["is_physicochemical_certified"]),
        overall_batch_released=bool(row["is_released"]),
        rejection_reasons=json.loads(row["rejection_reasons_json"]),
        certified_by_arn=row["certified_by_arn"],
        certification_timestamp=row["created_at"],
    )


@router.post("/safety/exposure-check", response_model=HeavyMetalExposureCheckResponse)
def check_heavy_metal_exposure(
    request: HeavyMetalExposureCheckRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> HeavyMetalExposureCheckResponse:
    """
    Check prescription against statutory Permitted Daily Exposure (PDE) limits.
    Prevents dispensing and raises clinical violation if daily exposure exceeds limits.
    """
    try:
        return evaluate_heavy_metal_exposure(request, conn)
    except HeavyMetalExposureExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            }
        )
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
