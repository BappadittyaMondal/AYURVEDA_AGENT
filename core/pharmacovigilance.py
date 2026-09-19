"""
core/pharmacovigilance.py - Core Engine for Phase 44: Pharmacovigilance & NPvCC Gateway.
Implements Modified Naranjo ASU Causality Algorithm and NPvCC Yellow Card serialization.
"""

import time
import uuid
import hashlib
import sqlite3
from typing import Optional, List, Tuple
from core.database import get_sqlite_connection, append_audit_log
from models.pharmacovigilance import (
    CausalityCategory,
    NpvccStatus,
    NaranjoAsuQuestions,
    SuspectedLotRecord,
    AdrReportCreate,
    AdrReportRecord,
    NpvccYellowCardExport,
)
from models.schemas import UserResponse


class PharmacovigilanceError(Exception):
    pass


def calculate_naranjo_asu_score(q: NaranjoAsuQuestions) -> Tuple[int, CausalityCategory]:
    """
    Computes Modified Naranjo ASU (Ayurveda, Siddha, Unani) ADR Causality Score:
    Score >= 9: Certain
    Score 5 - 8: Probable
    Score 1 - 4: Possible
    Score <= 0: Unlikely
    """
    score = 0
    score += 1 if q.previous_conclusive_reports else 0
    score += 2 if q.onset_after_drug else -1
    score += 1 if q.dechallenge_improvement else 0
    score += 2 if q.rechallenge_recurrence else 0
    score += 2 if q.alternative_causes_absent else -1
    score += 1 if q.toxic_concentration_or_heavy_metal else 0
    score += 1 if q.dose_response_gradient else 0
    score += 1 if q.past_history_similar else 0
    score += 1 if q.objective_laboratory_evidence else 0

    if score >= 9:
        cat = CausalityCategory.CERTAIN
    elif 5 <= score <= 8:
        cat = CausalityCategory.PROBABLE
    elif 1 <= score <= 4:
        cat = CausalityCategory.POSSIBLE
    else:
        cat = CausalityCategory.UNLIKELY

    return score, cat


def create_adr_report(
    req: AdrReportCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> AdrReportRecord:
    """Records an adverse drug reaction under statutory Pharmacovigilance Programme of India (PvPI)."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        score, causality = calculate_naranjo_asu_score(req.naranjo_questions)
        report_id = f"adr-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO adr_pharmacovigilance_reports (
                report_id, patient_id, hospital_id, suspected_formulation, batch_number,
                adverse_reaction_description, onset_latency_hours, naranjo_asu_score,
                causality_category, action_taken, reporting_rmp_arn, npvcc_submission_status,
                reported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                report_id,
                req.patient_id,
                req.hospital_id,
                req.suspected_formulation,
                req.batch_number,
                req.adverse_reaction_description,
                req.onset_latency_hours,
                score,
                causality.value,
                req.action_taken,
                req.reporting_rmp_arn,
                NpvccStatus.DRAFT.value,
                now,
            )
        )

        lot_record = None
        if req.suspected_lot_details:
            lot_id = f"lot-{uuid.uuid4().hex[:12]}"
            lot_in = req.suspected_lot_details
            cursor.execute(
                """
                INSERT INTO suspected_formulation_lots (
                    lot_id, report_id, formulation_name, manufacturer_name,
                    mfg_license_number, expiry_date, chemical_heavy_metal_audit_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    lot_id,
                    report_id,
                    lot_in.formulation_name,
                    lot_in.manufacturer_name,
                    lot_in.mfg_license_number,
                    lot_in.expiry_date,
                    lot_in.chemical_heavy_metal_audit_notes,
                    now,
                )
            )
            lot_record = SuspectedLotRecord(
                lot_id=lot_id,
                report_id=report_id,
                formulation_name=lot_in.formulation_name,
                manufacturer_name=lot_in.manufacturer_name,
                mfg_license_number=lot_in.mfg_license_number,
                expiry_date=lot_in.expiry_date,
                chemical_heavy_metal_audit_notes=lot_in.chemical_heavy_metal_audit_notes,
                created_at=now
            )

        user_id = current_user.user_id if current_user else req.reporting_rmp_arn
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "CREATE_ADR_REPORT",
            "PHARMACOVIGILANCE_REPORT",
            report_id,
            {
                "formulation": req.suspected_formulation,
                "naranjo_score": score,
                "causality": causality.value
            }
        )
        conn.commit()

        return AdrReportRecord(
            report_id=report_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            suspected_formulation=req.suspected_formulation,
            batch_number=req.batch_number,
            adverse_reaction_description=req.adverse_reaction_description,
            onset_latency_hours=req.onset_latency_hours,
            naranjo_asu_score=score,
            causality_category=causality,
            action_taken=req.action_taken,
            reporting_rmp_arn=req.reporting_rmp_arn,
            npvcc_submission_status=NpvccStatus.DRAFT,
            suspected_lot=lot_record,
            reported_at=now
        )
    finally:
        if should_close:
            conn.close()


def export_npvcc_yellow_card(
    report_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> NpvccYellowCardExport:
    """Serializes ADR report into statutory NPvCC Yellow Card XML format."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM adr_pharmacovigilance_reports WHERE report_id = ?;", (report_id,))
        row = cursor.fetchone()
        if not row:
            raise PharmacovigilanceError(f"ADR Report '{report_id}' not found.")

        # Anonymized patient hash
        pat_hash = hashlib.sha256(row["patient_id"].encode("utf-8")).hexdigest()[:16]
        utc_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<NPvCC_YellowCard_Form>
    <Header>
        <ReportID>{row["report_id"]}</ReportID>
        <HospitalID>{row["hospital_id"]}</HospitalID>
        <SubmissionTimestamp>{utc_time}</SubmissionTimestamp>
        <ReportingRmpARN>{row["reporting_rmp_arn"]}</ReportingRmpARN>
    </Header>
    <PatientData>
        <AnonymizedHash>{pat_hash}</AnonymizedHash>
    </PatientData>
    <SuspectedFormulation>
        <Name>{row["suspected_formulation"]}</Name>
        <BatchNumber>{row["batch_number"] or "NOT_SPECIFIED"}</BatchNumber>
        <LatencyHours>{row["onset_latency_hours"] or 0}</LatencyHours>
    </SuspectedFormulation>
    <AdverseEvent>
        <Description>{row["adverse_reaction_description"]}</Description>
        <ActionTaken>{row["action_taken"]}</ActionTaken>
    </AdverseEvent>
    <CausalityAssessment>
        <Algorithm>MODIFIED_NARANJO_ASU</Algorithm>
        <Score>{row["naranjo_asu_score"]}</Score>
        <Category>{row["causality_category"]}</Category>
    </CausalityAssessment>
</NPvCC_YellowCard_Form>"""

        cursor.execute(
            "UPDATE adr_pharmacovigilance_reports SET npvcc_submission_status = ? WHERE report_id = ?;",
            (NpvccStatus.SUBMITTED.value, report_id)
        )
        conn.commit()

        return NpvccYellowCardExport(
            report_id=row["report_id"],
            reporting_centre="National Pharmacovigilance Centre for ASU Drugs (NPvCC)",
            patient_identifier_hash=pat_hash,
            suspected_formulation=row["suspected_formulation"],
            reaction_terms=[row["adverse_reaction_description"]],
            naranjo_score=row["naranjo_asu_score"],
            causality=CausalityCategory(row["causality_category"]),
            submission_timestamp_utc=utc_time,
            xml_payload_preview=xml_payload
        )
    finally:
        if should_close:
            conn.close()


def get_patient_adr_reports(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[AdrReportRecord]:
    """Fetches ADR reports for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM adr_pharmacovigilance_reports
            WHERE patient_id = ?
            ORDER BY reported_at DESC;
            """,
            (patient_id,)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            cursor.execute("SELECT * FROM suspected_formulation_lots WHERE report_id = ?;", (r["report_id"],))
            lot_row = cursor.fetchone()
            lot_rec = None
            if lot_row:
                lot_rec = SuspectedLotRecord(
                    lot_id=lot_row["lot_id"],
                    report_id=lot_row["report_id"],
                    formulation_name=lot_row["formulation_name"],
                    manufacturer_name=lot_row["manufacturer_name"],
                    mfg_license_number=lot_row["mfg_license_number"],
                    expiry_date=lot_row["expiry_date"],
                    chemical_heavy_metal_audit_notes=lot_row["chemical_heavy_metal_audit_notes"],
                    created_at=lot_row["created_at"]
                )

            results.append(
                AdrReportRecord(
                    report_id=r["report_id"],
                    patient_id=r["patient_id"],
                    hospital_id=r["hospital_id"],
                    suspected_formulation=r["suspected_formulation"],
                    batch_number=r["batch_number"],
                    adverse_reaction_description=r["adverse_reaction_description"],
                    onset_latency_hours=r["onset_latency_hours"],
                    naranjo_asu_score=r["naranjo_asu_score"],
                    causality_category=CausalityCategory(r["causality_category"]),
                    action_taken=r["action_taken"],
                    reporting_rmp_arn=r["reporting_rmp_arn"],
                    npvcc_submission_status=NpvccStatus(r["npvcc_submission_status"]),
                    suspected_lot=lot_rec,
                    reported_at=r["reported_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()
