"""
Phase 16: Integration Test Suite for Dravya Guna Classical Herbology API.
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
        test_db_path = Path(tmpdir) / "dravyaguna_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "dravyaguna_api_test.db")

        with TestClient(app) as client:
            yield client


def test_herbs_listing_and_filtering_endpoints(client_with_db):
    """Verify herbs listing, text query search, and pharmacological filters."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all herbs
    resp = client_with_db.get("/api/v1/dravyaguna/herbs", headers=headers)
    assert resp.status_code == 200
    herbs = resp.json()
    assert len(herbs) >= 25

    # 3. Search by text 'Withania'
    resp_ashwa = client_with_db.get("/api/v1/dravyaguna/herbs?q=Withania", headers=headers)
    assert resp_ashwa.status_code == 200
    ashwa_list = resp_ashwa.json()
    assert len(ashwa_list) == 1
    assert ashwa_list[0]["herb_id"] == "HERB-ASHWAGANDHA"
    assert ashwa_list[0]["botanical_family"] == "Solanaceae"

    # 4. Filter by Veerya USHNA
    resp_ushna = client_with_db.get("/api/v1/dravyaguna/herbs?veerya=USHNA", headers=headers)
    assert resp_ushna.status_code == 200
    ushna_herbs = resp_ushna.json()
    assert len(ushna_herbs) >= 10
    for h in ushna_herbs:
        assert h["veerya"] == "USHNA"

    # 5. Filter by Rasa TIKTA
    resp_tikta = client_with_db.get("/api/v1/dravyaguna/herbs?rasa=TIKTA", headers=headers)
    assert resp_tikta.status_code == 200
    tikta_herbs = resp_tikta.json()
    assert len(tikta_herbs) >= 10
    for h in tikta_herbs:
        assert "TIKTA" in h["rasa"]

    # 6. Filter by Karma 'Rasayana'
    resp_rasayana = client_with_db.get("/api/v1/dravyaguna/herbs?karma=Rasayana", headers=headers)
    assert resp_rasayana.status_code == 200
    rasayana_herbs = resp_rasayana.json()
    assert len(rasayana_herbs) >= 5
    rasayana_ids = [h["herb_id"] for h in rasayana_herbs]
    assert "HERB-GUDUCHI" in rasayana_ids
    assert "HERB-AMALAKI" in rasayana_ids


def test_herb_profile_and_doshic_impact_endpoints(client_with_db):
    """Verify single herb retrieval and Doshic modulation score calculation."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get specific herb profile: Guduchi
    resp_guduchi = client_with_db.get("/api/v1/dravyaguna/herbs/HERB-GUDUCHI", headers=headers)
    assert resp_guduchi.status_code == 200
    data = resp_guduchi.json()
    assert data["herb_id"] == "HERB-GUDUCHI"
    assert data["botanical_name"] == "Tinospora cordifolia (Willd.) Miers"
    assert data["veerya"] == "USHNA"
    assert data["vipaka"] == "MADHURA"
    assert len(data["phytochemicals"]) >= 2
    assert len(data["dosages"]) >= 1

    # 3. Get Doshic impact vector for Guduchi
    resp_impact = client_with_db.get("/api/v1/dravyaguna/herbs/HERB-GUDUCHI/doshic-impact", headers=headers)
    assert resp_impact.status_code == 200
    impact = resp_impact.json()
    assert impact["herb_id"] == "HERB-GUDUCHI"
    assert impact["vata_delta"] <= 0.0
    assert impact["pitta_delta"] <= 0.0
    assert impact["kapha_delta"] <= 0.0
    assert len(impact["rationale"]) > 0

    # 4. Non-existent herb returns 404
    resp_404_herb = client_with_db.get("/api/v1/dravyaguna/herbs/HERB-UNKNOWN-999", headers=headers)
    assert resp_404_herb.status_code == 404

    resp_404_impact = client_with_db.get("/api/v1/dravyaguna/herbs/HERB-UNKNOWN-999/doshic-impact", headers=headers)
    assert resp_404_impact.status_code == 404
