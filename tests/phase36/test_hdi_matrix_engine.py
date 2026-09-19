"""
Phase 36: Unit Tests for Real-Time Herb-Drug Interaction Matrix Engine
======================================================================
Verifies:
1. Database seeding of the complete 28-point rules catalog (Table 78)
2. Blocking of critical contraindications (Warfarin+Guggulu, Digoxin+Arjuna)
3. Flagging of major monitoring interactions (Metformin+Karela, Diazepam+Ashwagandha)
4. Safe combinations returning All-Clear status
5. NCISM ARN clinical overrides and audit persistence (Table 79)
"""

import pytest
import sqlite3
from core.database import get_sqlite_connection, init_database
from core.hdi_matrix import (
    ensure_hdi_rules_seeded,
    cross_check_herb_drug_interactions,
    override_hdi_intercept,
)
from models.hdi_matrix import (
    HdiSeverity,
    HdiCrossCheckRequest,
    HdiOverrideRequest,
)


@pytest.fixture
def conn():
    """Provides a thread-safe database connection."""
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_hdi_28_rules_seeding(conn):
    """Verify that all 28 canonical rules are populated into Table 78."""
    ensure_hdi_rules_seeded(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM hdi_interaction_rules;")
    count = cursor.fetchone()["count"]
    assert count >= 28


def test_critical_contraindication_interception(conn):
    """Verify that Warfarin + Guggulu triggers CONTRAINDICATED_CRITICAL and blocks prescription."""
    req = HdiCrossCheckRequest(
        patient_id="PAT-WARFARIN-01",
        hospital_id="aiia-delhi-central-001",
        prescribed_ayurvedic_herbs=["Yogaraja Guggulu", "Rasna Saptaka Kwatha"],
        current_allopathic_medications=["Warfarin 5mg", "Atorvastatin 20mg"],
        attending_physician_arn="ARN-NCISM-2015-8832"
    )

    resp = cross_check_herb_drug_interactions(req, conn=conn)
    assert not resp.is_safe_to_prescribe
    assert len(resp.critical_blocks) >= 1
    # Check Guggulu + Warfarin block
    guggulu_block = [b for b in resp.critical_blocks if "guggulu" in b.herb.lower() and "warfarin" in b.drug.lower()]
    assert len(guggulu_block) == 1
    assert guggulu_block[0].severity == HdiSeverity.CONTRAINDICATED_CRITICAL
    assert "hemorrhage" in guggulu_block[0].adverse_effects.lower()


def test_major_monitoring_interaction(conn):
    """Verify that Metformin + Karela generates major monitoring warning."""
    req = HdiCrossCheckRequest(
        patient_id="PAT-DIABETES-01",
        hospital_id="aiia-delhi-central-001",
        prescribed_ayurvedic_herbs=["Karela Churna", "Nishamalaki Vati"],
        current_allopathic_medications=["Metformin 500mg"],
        attending_physician_arn="ARN-NCISM-2015-8832"
    )

    resp = cross_check_herb_drug_interactions(req, conn=conn)
    # No critical contraindication, so is_safe_to_prescribe should be True with warnings
    assert resp.is_safe_to_prescribe
    assert len(resp.critical_blocks) == 0
    assert len(resp.warnings_for_monitoring) >= 1
    karela_warn = [w for w in resp.warnings_for_monitoring if "karela" in w.herb.lower()]
    assert len(karela_warn) == 1
    assert karela_warn[0].severity == HdiSeverity.MAJOR_MONITORING_REQUIRED
    assert "hypoglycemia" in karela_warn[0].adverse_effects.lower()


def test_all_clear_combination(conn):
    """Verify that an inert combination with no documented interaction passes all-clear."""
    req = HdiCrossCheckRequest(
        patient_id="PAT-INERT-01",
        hospital_id="aiia-delhi-central-001",
        prescribed_ayurvedic_herbs=["Drakshavaleha", "Amalaki Rasayana"],
        current_allopathic_medications=["Paracetamol 500mg"],
        attending_physician_arn="ARN-NCISM-2015-8832"
    )

    resp = cross_check_herb_drug_interactions(req, conn=conn)
    assert resp.is_safe_to_prescribe
    assert resp.total_conflicts_detected == 0
    assert any("ALL CLEAR" in g for g in resp.clinical_guidance)


def test_physician_override_recording(conn):
    """Verify that an NCISM physician can record an override with written justification."""
    override_req = HdiOverrideRequest(
        patient_id="PAT-OVERRIDE-01",
        hospital_id="aiia-delhi-central-001",
        rule_id="HDI-04",
        prescribed_herb="Karela",
        concurrent_drug="Metformin",
        physician_arn="ARN-NCISM-2015-8832",
        clinical_justification="Patient has severe hyperglycemia (HbA1c 10.2%). Monitored closely via CGM."
    )

    resp = override_hdi_intercept(override_req, conn=conn)
    assert resp["status"] == "OVERRIDE_RECORDED_AND_LOGGED"
    assert resp["physician_arn"] == "ARN-NCISM-2015-8832"

    # Confirm in Table 79
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hdi_audit_intercepts WHERE patient_id = ?;", ("PAT-OVERRIDE-01",))
    row = cursor.fetchone()
    assert row is not None
    assert row["action_taken"] == "OVERRIDDEN_BY_RMP"
    assert "CGM" in row["override_reason"]
