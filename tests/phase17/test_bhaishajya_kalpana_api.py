"""
Phase 17: Integration Test Suite for Bhaishajya Kalpana Classical Formulations & Synergy API.
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
        test_db_path = Path(tmpdir) / "kalpana_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "kalpana_api_test.db")

        with TestClient(app) as client:
            yield client


def test_formulations_listing_and_filtering_endpoints(client_with_db):
    """Verify formulation listing, text search, and Kalpana filters."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all formulations
    resp = client_with_db.get("/api/v1/bhaishajya-kalpana/formulations", headers=headers)
    assert resp.status_code == 200
    forms = resp.json()
    assert len(forms) >= 15

    # 3. Filter by Kalpana 'CHURNA'
    resp_churna = client_with_db.get("/api/v1/bhaishajya-kalpana/formulations?kalpana=CHURNA", headers=headers)
    assert resp_churna.status_code == 200
    churna_list = resp_churna.json()
    assert len(churna_list) >= 4
    for c in churna_list:
        assert c["kalpana_form"] == "CHURNA"

    # 4. Filter by indication 'Amavata'
    resp_amavata = client_with_db.get("/api/v1/bhaishajya-kalpana/formulations?indication=Amavata", headers=headers)
    assert resp_amavata.status_code == 200
    ama_forms = resp_amavata.json()
    assert len(ama_forms) >= 1
    ama_ids = [f["formulation_id"] for f in ama_forms]
    assert "FORM-YOGARAJA-GUGGULU" in ama_ids or "FORM-TRIKATU" in ama_ids


def test_formulation_detail_and_anupana_endpoints(client_with_db):
    """Verify formulation detail query and Anupana matrix catalog."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get specific formulation detail: Chyavanaprasha
    resp_detail = client_with_db.get("/api/v1/bhaishajya-kalpana/formulations/FORM-CHYAVANAPRASH", headers=headers)
    assert resp_detail.status_code == 200
    data = resp_detail.json()
    assert data["formulation_id"] == "FORM-CHYAVANAPRASH"
    assert data["kalpana_form"] == "AVALEHA"
    assert len(data["ingredients"]) >= 3
    assert data["standard_anupana"] == "ANUPANA-KSHEERA"

    # 3. Invalid formulation returns 404
    resp_404 = client_with_db.get("/api/v1/bhaishajya-kalpana/formulations/FORM-NONEXISTENT-999", headers=headers)
    assert resp_404.status_code == 404

    # 4. Get Anupana catalog
    resp_anupana = client_with_db.get("/api/v1/bhaishajya-kalpana/anupana", headers=headers)
    assert resp_anupana.status_code == 200
    anupana_list = resp_anupana.json()
    assert len(anupana_list) >= 8
    anupana_ids = [a["anupana_id"] for a in anupana_list]
    assert "ANUPANA-MADHU" in anupana_ids
    assert "ANUPANA-GHRITA" in anupana_ids
    assert "ANUPANA-TAKRA" in anupana_ids


def test_evaluate_synergy_and_viruddha_firewalls(client_with_db):
    """Verify custom polyherbal synergy evaluation and Viruddha safety warnings."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Custom polyherbal recipe with equal 1:1 Honey & Ghee -> should flag Viruddha warning
    synergy_payload = {
        "ingredients": [
            {"herb_id": "HERB-ASHWAGANDHA", "herb_name": "Ashwagandha", "proportion_parts": 2.0},
            {"herb_id": "HERB-GUDUCHI", "herb_name": "Guduchi", "proportion_parts": 1.0}
        ],
        "proposed_anupana_id": "ANUPANA-MADHU",
        "honey_ratio_parts": 5.0,
        "ghee_ratio_parts": 5.0,
        "is_heated_anupana": True
    }

    resp = client_with_db.post(
        "/api/v1/bhaishajya-kalpana/evaluate-synergy",
        json=synergy_payload,
        headers=headers
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert "vata_delta" in res_data["aggregate_doshic_vector"]
    assert len(res_data["safety_warnings"]) >= 2
    codes = [w["code"] for w in res_data["safety_warnings"]]
    assert "VIRUDDHA_SAMYOGA_MADHU_GHRITA" in codes
    assert "VIRUDDHA_USHNA_MADHU" in codes
