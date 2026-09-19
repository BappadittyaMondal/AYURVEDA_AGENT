"""
Unit Tests for Clinical Dietetics, Ahara Varga, Pathya-Apathya & Viruddha Ahara Engine (Phase 21).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.dietetics import (
    SEED_DIET_INGREDIENTS,
    SEED_PATHYA_APATHYA_REGISTRY,
    audit_viruddha_ahara,
    create_and_evaluate_diet_plan,
    get_disease_pathya_guidelines,
    get_ingredient_profile,
    initialize_dietetics_tables,
    list_all_ingredients,
)
from models.dietetics import (
    AharaVarga,
    DietPlanCreateRequest,
    MealItem,
    PlannedMeal,
    ViruddhaType,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_dietetics.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_dietetics_tables(conn)

    # Seed patient
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-DIET-001", "aiia-delhi-central-001", "Raghavendra", "Sharma", "1978-04-20", "MALE", "+919876543299", 1700000000)
    )
    return tmpdir, conn


def test_diet_ingredients_catalog_completeness():
    """Verify registry contains 24+ ingredients covering all 12 classical Ahara Vargas."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        ingredients = list_all_ingredients(conn)
        assert len(ingredients) >= 24

        vargas_found = {ing.ahara_varga for ing in ingredients}
        # Check presence of major Ahara Vargas
        assert AharaVarga.SHUKA_DHANYA in vargas_found
        assert AharaVarga.SHAMI_DHANYA in vargas_found
        assert AharaVarga.GORASA_VARGA in vargas_found
        assert AharaVarga.IKSHU_VARGA in vargas_found
        assert AharaVarga.SHAKA_VARGA in vargas_found
        assert AharaVarga.PHALA_VARGA in vargas_found
        assert AharaVarga.MAMSA_VARGA in vargas_found
        assert AharaVarga.HARITA_VARGA in vargas_found
        assert AharaVarga.AHARAYOGI_VARGA in vargas_found

        # Check key ingredient profiles
        raktashali = get_ingredient_profile("ING-RAKTASHALI", conn)
        assert raktashali.rasa == "Madhura"
        assert raktashali.veerya == "Sheeta"
        assert raktashali.calories_per_100g > 300.0

        madhu = get_ingredient_profile("ING-MADHU", conn)
        assert "Lekhana" in madhu.guna
        assert madhu.vipaka == "Katu"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_disease_pathya_apathya_registry():
    """Verify disease-specific Pathya and Apathya guidelines for major conditions."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        amavata = get_disease_pathya_guidelines("AYU-DIS-AMAVATA", conn)
        assert amavata is not None
        assert any("यव" in p for p in amavata.pathya_ahara)
        assert any("दधि" in a for a in amavata.apathya_ahara)

        prameha = get_disease_pathya_guidelines("AYU-DIS-PRAMEHA", conn)
        assert prameha is not None
        assert any("कारवेल्लक" in p for p in prameha.pathya_ahara)
        assert any("गुड" in a for a in prameha.apathya_ahara)

        amlapitta = get_disease_pathya_guidelines("AYU-DIS-AMLAPITTA", conn)
        assert amlapitta is not None
        assert any("दाडिम" in p for p in amlapitta.pathya_ahara)
        assert any("मद्य" in a for a in amlapitta.apathya_ahara)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_viruddha_veerya_fish_and_milk():
    """Verify Veerya Viruddha: Fish + Milk combination is flagged as CRITICAL_BLOCKED."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        meal = PlannedMeal(
            meal_name="MADHYAHNA",
            time_of_day="01:00 PM",
            items=[
                MealItem(ingredient_id="ING-MATSYA", portion_grams=150.0),
                MealItem(ingredient_id="ING-GODUGDHA", portion_grams=200.0),
            ]
        )
        violations = audit_viruddha_ahara([meal], conn)
        assert len(violations) >= 1
        veerya_viol = next((v for v in violations if v.viruddha_type == ViruddhaType.VEERYA_VIRUDDHA), None)
        assert veerya_viol is not None
        assert veerya_viol.severity == "CRITICAL_BLOCKED"
        assert "Veerya Viruddha" in veerya_viol.clinical_rationale
    finally:
        conn.close()
        tmpdir.cleanup()


def test_viruddha_matra_honey_and_ghee_equal_ratio():
    """Verify Matra Viruddha: Honey + Ghee in equal 1:1 weight is CRITICAL_BLOCKED."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Equal ratio (15g each)
        meal_equal = PlannedMeal(
            meal_name="PRATARASHA",
            time_of_day="08:00 AM",
            items=[
                MealItem(ingredient_id="ING-MADHU", portion_grams=15.0),
                MealItem(ingredient_id="ING-GHRITA", portion_grams=15.0),
            ]
        )
        violations_equal = audit_viruddha_ahara([meal_equal], conn)
        matra_viol = next((v for v in violations_equal if v.viruddha_type == ViruddhaType.MATRA_VIRUDDHA), None)
        assert matra_viol is not None
        assert matra_viol.severity == "CRITICAL_BLOCKED"
        assert "Matra Viruddha" in matra_viol.clinical_rationale

        # Unequal ratio (20g Honey + 5g Ghee) -> compliant
        meal_unequal = PlannedMeal(
            meal_name="PRATARASHA",
            time_of_day="08:00 AM",
            items=[
                MealItem(ingredient_id="ING-MADHU", portion_grams=20.0),
                MealItem(ingredient_id="ING-GHRITA", portion_grams=5.0),
            ]
        )
        violations_unequal = audit_viruddha_ahara([meal_unequal], conn)
        assert not any(v.viruddha_type == ViruddhaType.MATRA_VIRUDDHA for v in violations_unequal)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_viruddha_samskara_heated_honey():
    """Verify Samskara Viruddha: Heated honey is CRITICAL_BLOCKED due to toxic Ama-Visha."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        meal = PlannedMeal(
            meal_name="SNACK",
            time_of_day="04:30 PM",
            items=[
                MealItem(ingredient_id="ING-MADHU", portion_grams=15.0, is_heated=True),
            ]
        )
        violations = audit_viruddha_ahara([meal], conn)
        samskara_viol = next((v for v in violations if v.viruddha_type == ViruddhaType.SAMSKARA_VIRUDDHA), None)
        assert samskara_viol is not None
        assert samskara_viol.severity == "CRITICAL_BLOCKED"
        assert "Ama-Visha" in samskara_viol.clinical_rationale
    finally:
        conn.close()
        tmpdir.cleanup()


def test_viruddha_samskara_heated_curd_and_kala_curd_at_night():
    """Verify Samskara (heated curd) and Kala Viruddha (curd at night) warnings."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Heated curd at noon
        meal_heated_curd = PlannedMeal(
            meal_name="MADHYAHNA",
            time_of_day="01:00 PM",
            items=[
                MealItem(ingredient_id="ING-DADHI", portion_grams=100.0, is_heated=True),
            ]
        )
        violations_heated = audit_viruddha_ahara([meal_heated_curd], conn)
        assert any(v.viruddha_type == ViruddhaType.SAMSKARA_VIRUDDHA for v in violations_heated)

        # Cold curd at dinner (Sayam)
        meal_night_curd = PlannedMeal(
            meal_name="DINNER",
            time_of_day="08:00 PM",
            items=[
                MealItem(ingredient_id="ING-DADHI", portion_grams=100.0, is_heated=False),
            ]
        )
        violations_night = audit_viruddha_ahara([meal_night_curd], conn)
        kala_viol = next((v for v in violations_night if v.viruddha_type == ViruddhaType.KALA_VIRUDDHA), None)
        assert kala_viol is not None
        assert kala_viol.severity == "WARNING"
        assert "Nishi Dadhi" in kala_viol.clinical_rationale
    finally:
        conn.close()
        tmpdir.cleanup()


def test_viruddha_samyoga_milk_and_banana():
    """Verify Samyoga Viruddha: Milk + Banana generates warning for Agni suppression."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        meal = PlannedMeal(
            meal_name="PRATARASHA",
            time_of_day="08:00 AM",
            items=[
                MealItem(ingredient_id="ING-GODUGDHA", portion_grams=200.0),
                MealItem(ingredient_id="ING-KADALI", portion_grams=100.0),
            ]
        )
        violations = audit_viruddha_ahara([meal], conn)
        samyoga_viol = next((v for v in violations if v.viruddha_type == ViruddhaType.SAMYOGA_VIRUDDHA), None)
        assert samyoga_viol is not None
        assert samyoga_viol.severity == "WARNING"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_create_diet_plan_success_and_nutritional_calculus():
    """Verify wholesome meal plan computation, macronutrient sums, Doshic vector, and Pathya score."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = DietPlanCreateRequest(
            patient_id="PAT-DIET-001",
            diagnosis_code="AYU-DIS-AMAVATA",
            target_calories=1800.0,
            prescribed_by_arn="AY-DL-2024-998811",
            meals=[
                PlannedMeal(
                    meal_name="PRATARASHA",
                    time_of_day="08:00 AM",
                    items=[
                        MealItem(ingredient_id="ING-YAVA", portion_grams=100.0),      # 352 kcal, 12.5g P, 73.5g C
                        MealItem(ingredient_id="ING-TAKRA", portion_grams=200.0),     # 80 kcal, 6.0g P, 9.6g C
                    ]
                ),
                PlannedMeal(
                    meal_name="MADHYAHNA",
                    time_of_day="01:00 PM",
                    items=[
                        MealItem(ingredient_id="ING-RAKTASHALI", portion_grams=150.0), # 517.5 kcal
                        MealItem(ingredient_id="ING-KULATTHA", portion_grams=100.0),   # 321 kcal
                        MealItem(ingredient_id="ING-PATOLA", portion_grams=100.0),     # 20 kcal
                        MealItem(ingredient_id="ING-ARDRAKA", portion_grams=10.0),     # 8 kcal
                    ]
                ),
            ]
        )

        plan = create_and_evaluate_diet_plan(req, "aiia-delhi-central-001", conn)

        assert plan.diet_plan_id.startswith("DIET-PAT-DIET-001-")
        assert plan.total_calories > 1000.0
        assert plan.total_protein_g > 30.0
        assert plan.viruddha_check_passed is True
        assert plan.pathya_compliance_score > 50.0
        assert "delta_vata" in plan.composite_doshic_vector
        assert "delta_pitta" in plan.composite_doshic_vector
        assert "delta_kapha" in plan.composite_doshic_vector

        # Verify persisted in database
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_diet_prescriptions WHERE diet_plan_id = ?;", (plan.diet_plan_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["patient_id"] == "PAT-DIET-001"
        assert row["viruddha_check_passed"] == 1
    finally:
        conn.close()
        tmpdir.cleanup()


def test_create_diet_plan_blocked_on_critical_viruddha():
    """Verify that a meal plan with critical Viruddha Ahara is blocked by ClinicalGovernanceException."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = DietPlanCreateRequest(
            patient_id="PAT-DIET-001",
            diagnosis_code="AYU-DIS-AMAVATA",
            target_calories=2000.0,
            prescribed_by_arn="AY-DL-2024-998811",
            meals=[
                PlannedMeal(
                    meal_name="MADHYAHNA",
                    time_of_day="01:00 PM",
                    items=[
                        MealItem(ingredient_id="ING-MATSYA", portion_grams=150.0),
                        MealItem(ingredient_id="ING-GODUGDHA", portion_grams=200.0),
                    ]
                )
            ]
        )

        with pytest.raises(ClinicalGovernanceException) as exc_info:
            create_and_evaluate_diet_plan(req, "aiia-delhi-central-001", conn)

        assert "CRITICAL_VIRUDDHA_AHARA_BLOCKED" in str(exc_info.value.error_code)
    finally:
        conn.close()
        tmpdir.cleanup()
