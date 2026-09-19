"""
Integration Tests for Rasa Shastra & Herbo-Mineral Processing Safety API (Phase 18).
"""

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from config.settings import get_settings
from core.database import init_database
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "rasashastra_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "rasashastra_api_test.db")

        with TestClient(app) as client:
            yield client


def test_minerals_listing_and_filtering_endpoints(client_with_db):
    """Verify minerals catalog listing, text search, and category filters."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all minerals
    resp = client_with_db.get("/api/v1/rasashastra/minerals", headers=headers)
    assert resp.status_code == 200
    minerals = resp.json()
    assert len(minerals) >= 18

    # 3. Filter by category 'DHATU_SHUDDHA'
    resp_metals = client_with_db.get("/api/v1/rasashastra/minerals?category=DHATU_SHUDDHA", headers=headers)
    assert resp_metals.status_code == 200
    metals = resp_metals.json()
    assert len(metals) == 4
    metal_ids = [m["mineral_id"] for m in metals]
    assert "MIN-SUVARNA" in metal_ids
    assert "MIN-RAJATA" in metal_ids
    assert "MIN-TAMRA" in metal_ids
    assert "MIN-LAUHA" in metal_ids

    # 4. Filter by Schedule E(1) poisons
    resp_e1 = client_with_db.get("/api/v1/rasashastra/minerals?schedule_e1_only=true", headers=headers)
    assert resp_e1.status_code == 200
    e1_items = resp_e1.json()
    assert len(e1_items) >= 7
    e1_ids = [m["mineral_id"] for m in e1_items]
    assert "MIN-PARADA" in e1_ids
    assert "MIN-HARATALA" in e1_ids
    assert "MIN-VATSANABHA" in e1_ids

    # 5. Search query
    resp_q = client_with_db.get("/api/v1/rasashastra/minerals?q=Gold", headers=headers)
    assert resp_q.status_code == 200
    found = resp_q.json()
    assert any(m["mineral_id"] == "MIN-SUVARNA" for m in found)


def test_mineral_detail_endpoint(client_with_db):
    """Verify single mineral lookup and 404 behavior."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch valid mineral
    resp = client_with_db.get("/api/v1/rasashastra/minerals/MIN-ABHRAKA", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["mineral_id"] == "MIN-ABHRAKA"
    assert detail["category"] == "MAHARASA"
    assert detail["minimum_puta_cycles"] >= 30

    # Fetch invalid mineral
    resp_404 = client_with_db.get("/api/v1/rasashastra/minerals/MIN-NONEXISTENT", headers=headers)
    assert resp_404.status_code == 404


def test_shodhana_verification_and_compliance_endpoints(client_with_db):
    """Verify Shodhana recording and statutory Schedule E(1) compliance check."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check compliance on unpurified Vatsanabha -> should fail 422
    resp_pre = client_with_db.get(
        "/api/v1/rasashastra/shodhana/check-compliance/MIN-VATSANABHA?batch_id=RAW-BATCH-99",
        headers=headers,
    )
    assert resp_pre.status_code == 422

    # 2. Certify Shodhana for Vatsanabha
    shodhana_payload = {
        "batch_id": "RAW-BATCH-99",
        "mineral_id": "MIN-VATSANABHA",
        "method": "SWEDANA_DOLA_YANTRA",
        "media_used": ["Godugdha (Cow Milk)"],
        "cycles_completed": 1,
        "organoleptic_shuddhi_confirmed": True,
        "verified_by_arn": "ARN-NCISM-2015-8832",
        "notes": "Purified strictly per Rasashastra Samhita guidelines",
    }
    resp_shodhana = client_with_db.post(
        "/api/v1/rasashastra/shodhana/verify",
        json=shodhana_payload,
        headers=headers,
    )
    assert resp_shodhana.status_code == 200
    shodhana_res = resp_shodhana.json()
    assert shodhana_res["is_verified"] is True

    # 3. Compliance check should now succeed 200
    resp_post = client_with_db.get(
        "/api/v1/rasashastra/shodhana/check-compliance/MIN-VATSANABHA?batch_id=RAW-BATCH-99",
        headers=headers,
    )
    assert resp_post.status_code == 200
    assert resp_post.json()["is_shodhana_compliant"] is True


def test_bhasma_batch_release_and_retrieval_endpoints(client_with_db):
    """Verify Bhasma batch laboratory release evaluation and analytical certificate retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Release a fully compliant batch of Yashada Bhasma
    compliant_payload = {
        "batch_id": "BATCH-YASHADA-QC-PASS",
        "mineral_id": "MIN-YASHADA",
        "formulation_name": "Yashada Bhasma",
        "puta_type": "KUKKUTA_PUTA",
        "putas_completed": 7,
        "classical_pariksha": {
            "varitara": True,
            "unama": True,
            "rekhapurna": True,
            "apunarbhava": True,
            "niruttha": True,
            "nis_svadu": True,
            "nischandrika": True,
        },
        "elemental_assay": {
            "lead_pb_ppm": 1.5,
            "arsenic_as_ppm": 0.8,
            "cadmium_cd_ppm": 0.05,
            "mercury_hg_ppm": 0.1,
            "active_metal_name": "Zinc",
            "active_metal_percentage": 56.2,
            "free_ionic_toxic_metal_ppm": 0.0,
        },
        "particle_size": {
            "d10_microns": 0.5,
            "d50_microns": 2.4,
            "d90_microns": 8.1,
            "nanoscale_percentage": 30.5,
        },
        "certified_by_arn": "ARN-NCISM-2015-8832",
    }

    resp_release = client_with_db.post(
        "/api/v1/rasashastra/bhasma/batch-release",
        json=compliant_payload,
        headers=headers,
    )
    assert resp_release.status_code == 200
    cert = resp_release.json()
    assert cert["is_classical_certified"] is True
    assert cert["overall_batch_released"] is True
    assert len(cert["rejection_reasons"]) == 0

    # 2. Retrieve certificate
    resp_get = client_with_db.get("/api/v1/rasashastra/bhasma/batches/BATCH-YASHADA-QC-PASS", headers=headers)
    assert resp_get.status_code == 200
    retrieved = resp_get.json()
    assert retrieved["batch_id"] == "BATCH-YASHADA-QC-PASS"
    assert retrieved["overall_batch_released"] is True

    # 3. Release a rejected batch (heavy metal lead contamination: 28 ppm > 10 ppm)
    failing_payload = dict(compliant_payload)
    failing_payload["batch_id"] = "BATCH-YASHADA-QC-FAIL"
    failing_payload["elemental_assay"] = {
        "lead_pb_ppm": 28.0,  # Exceeds limit
        "arsenic_as_ppm": 0.8,
        "cadmium_cd_ppm": 0.05,
        "mercury_hg_ppm": 0.1,
        "active_metal_name": "Zinc",
        "active_metal_percentage": 56.2,
        "free_ionic_toxic_metal_ppm": 0.0,
    }
    resp_fail = client_with_db.post(
        "/api/v1/rasashastra/bhasma/batch-release",
        json=failing_payload,
        headers=headers,
    )
    assert resp_fail.status_code == 200
    fail_cert = resp_fail.json()
    assert fail_cert["overall_batch_released"] is False
    assert any("Lead (Pb)" in r for r in fail_cert["rejection_reasons"])


def test_exposure_check_api_endpoint(client_with_db):
    """Verify Permitted Daily Exposure (PDE) verification endpoint."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup released batch
    client_with_db.post(
        "/api/v1/rasashastra/bhasma/batch-release",
        json={
            "batch_id": "BATCH-SWARNA-PDE-TEST",
            "mineral_id": "MIN-SUVARNA",
            "formulation_name": "Swarna Bhasma",
            "puta_type": "VARAHA_PUTA",
            "putas_completed": 10,
            "classical_pariksha": {
                "varitara": True, "unama": True, "rekhapurna": True,
                "apunarbhava": True, "niruttha": True, "nis_svadu": True, "nischandrika": True,
            },
            "elemental_assay": {
                "lead_pb_ppm": 1.0, "arsenic_as_ppm": 0.2, "cadmium_cd_ppm": 0.01,
                "mercury_hg_ppm": 0.05, "active_metal_name": "Gold",
                "active_metal_percentage": 99.0, "free_ionic_toxic_metal_ppm": 0.0,
            },
            "particle_size": {
                "d10_microns": 0.3, "d50_microns": 1.5, "d90_microns": 4.5, "nanoscale_percentage": 48.0,
            },
            "certified_by_arn": "ARN-NCISM-2015-8832",
        },
        headers=headers,
    )

    # 1. Normal therapeutic dose: 30 mg/day
    safe_resp = client_with_db.post(
        "/api/v1/rasashastra/safety/exposure-check",
        json={
            "patient_id": "patient-pde-01",
            "prescriptions": [
                {"batch_id": "BATCH-SWARNA-PDE-TEST", "daily_dose_mg": 30.0, "duration_days": 30}
            ],
        },
        headers=headers,
    )
    assert safe_resp.status_code == 200
    safe_data = safe_resp.json()
    assert safe_data["is_within_pde_limits"] is True
    assert safe_data["safety_verdict"] == "SAFE_AND_COMPLIANT"
