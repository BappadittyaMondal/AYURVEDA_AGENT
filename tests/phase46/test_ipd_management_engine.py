"""
tests/phase46/test_ipd_management_engine.py - Unit tests for Phase 46 IPD Inpatient Bed Management & Nursing Charting.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.ipd_management import (
    IpdBedStatus,
    BedAllocationCreate,
    NursingChartCreate,
)
from core.ipd_management import (
    allocate_ipd_bed,
    discharge_ipd_patient,
    record_nursing_chart,
    get_ward_bed_occupancy,
    get_patient_nursing_charts,
    IpdManagementError,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-ipd-test-01", "aiia-delhi-central-001", "Ramesh", "Gupta", "1968-10-14", "MALE", "+919833445566", 1700000000)
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-ipd-test-02", "aiia-delhi-central-001", "Kamla", "Devi", "1972-05-19", "FEMALE", "+919833445577", 1700000000)
    )
    # Clean up test beds
    cursor.execute("DELETE FROM panchakarma_daily_nursing_charts WHERE patient_id LIKE 'pat-ipd-test-%';")
    cursor.execute("DELETE FROM ipd_bed_allocations WHERE patient_id LIKE 'pat-ipd-test-%';")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def rmp_user():
    return UserResponse(
        user_id="user-physician-001",
        hospital_id="aiia-delhi-central-001",
        username="physician_rmp",
        full_name="Dr. Ananya Sen",
        arn="ARN-NCISM-2015-8832",
        role=ClinicalRole.PHYSICIAN_RMP,
        is_active=True,
        created_at=1700000000
    )


def test_bed_allocation_and_conflict_handling(conn, rmp_user):
    # Allocate bed 101 in Kayachikitsa Ward
    req = BedAllocationCreate(
        patient_id="pat-ipd-test-01",
        hospital_id="aiia-delhi-central-001",
        ward_name="KAYACHIKITSA_GENERAL",
        bed_number="BED-101",
        attending_rmp_arn="ARN-NCISM-2015-8832"
    )
    alloc = allocate_ipd_bed(req, current_user=rmp_user, conn=conn)
    assert alloc.allocation_id.startswith("ipd-")
    assert alloc.status == IpdBedStatus.OCCUPIED

    # Attempt to allocate the same occupied bed to another patient -> Error
    req_conflict = BedAllocationCreate(
        patient_id="pat-ipd-test-02",
        hospital_id="aiia-delhi-central-001",
        ward_name="KAYACHIKITSA_GENERAL",
        bed_number="BED-101",
        attending_rmp_arn="ARN-NCISM-2015-8832"
    )
    with pytest.raises(IpdManagementError):
        allocate_ipd_bed(req_conflict, current_user=rmp_user, conn=conn)


def test_nursing_chart_and_discharge_lifecycle(conn, rmp_user):
    req = BedAllocationCreate(
        patient_id="pat-ipd-test-02",
        hospital_id="aiia-delhi-central-001",
        ward_name="PANCHAKARMA_SUITE",
        bed_number="DRONI-BED-02",
        attending_rmp_arn="ARN-NCISM-2015-8832"
    )
    alloc = allocate_ipd_bed(req, current_user=rmp_user, conn=conn)

    # Record nursing chart round
    nrs_req = NursingChartCreate(
        allocation_id=alloc.allocation_id,
        patient_id="pat-ipd-test-02",
        vital_bp_systolic=124,
        vital_bp_diastolic=82,
        vital_pulse_bpm=74,
        panchakarma_therapy_administered="Virechana Karma with Trivrit Leha 30g",
        vega_count=8,
        jeerna_ahara_lakshana="Udgara Shuddhi, Utsaha, Laghava observed",
        nursing_notes="Patient tolerating Samsarjana Krama Peya well. No exhaustion.",
        nurse_name="Sister Lalitha Nair, B.Sc Nursing"
    )
    chart = record_nursing_chart(nrs_req, conn=conn)
    assert chart.chart_id.startswith("nrs-")
    assert chart.vega_count == 8

    charts = get_patient_nursing_charts(alloc.allocation_id, conn=conn)
    assert len(charts) >= 1
    assert charts[0].chart_id == chart.chart_id

    # Discharge patient
    discharged = discharge_ipd_patient(alloc.allocation_id, conn=conn)
    assert discharged.status == IpdBedStatus.DISCHARGED
    assert discharged.discharge_timestamp is not None
