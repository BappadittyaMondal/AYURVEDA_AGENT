"""
tests/test_clinical_benchmark_harness.py - Pytest automated verification for 50-Case Multi-Morbidity Benchmark.
"""

import pytest
from core.clinical_benchmark_harness import (
    build_50_benchmark_cases,
    execute_benchmark_case,
    run_full_50_case_benchmark,
)


def test_benchmark_cases_generation_and_count():
    """Verify that exactly 50 distinct multi-morbidity benchmark cases are defined across all 5 clinical domains."""
    cases = build_50_benchmark_cases()
    assert len(cases) == 50

    domains = {c.domain for c in cases}
    assert "KAYACHIKITSA" in domains
    assert "EMERGENCY_LETHAL_MIMIC" in domains
    assert "VULNERABLE_COHORT" in domains
    assert "SCHEDULE_E1_POISON" in domains
    assert "SHALYA_PARASURGICAL" in domains

    # Verify 10 cases per domain
    for d in domains:
        count = sum(1 for c in cases if c.domain == d)
        assert count == 10, f"Expected 10 cases in {d}, got {count}"


def test_lethal_mimic_emergency_ruleout_invariants():
    """Verify that all 10 emergency lethal mimic cases correctly trigger break-glass emergency transfer."""
    cases = [c for c in build_50_benchmark_cases() if c.domain == "EMERGENCY_LETHAL_MIMIC"]
    assert len(cases) == 10

    for c in cases:
        res = execute_benchmark_case(c)
        assert res.passed is True, f"Failed on {c.case_id}: {res.status_notes}"
        assert res.emergency_triggered is True, f"Emergency transfer failed for {c.case_id}"


def test_vulnerable_cohort_and_pregnancy_invariants():
    """Verify that pregnant cases block teratogenic herbs and pediatric cases enforce posology clamping."""
    cases = [c for c in build_50_benchmark_cases() if c.domain == "VULNERABLE_COHORT"]
    assert len(cases) == 10

    for c in cases:
        res = execute_benchmark_case(c)
        assert res.passed is True, f"Failed on {c.case_id}: {res.status_notes}"
        if c.expected_pregnancy_blocked:
            assert res.pregnancy_check_passed is True
        if c.expected_pediatric_clamped:
            assert res.pediatric_check_passed is True


def test_schedule_e1_poison_alerts():
    """Verify that all 10 Schedule E(1) toxic botanicals and minerals trigger statutory poison alerts."""
    cases = [c for c in build_50_benchmark_cases() if c.domain == "SCHEDULE_E1_POISON"]
    assert len(cases) == 10

    for c in cases:
        res = execute_benchmark_case(c)
        assert res.passed is True, f"Failed on {c.case_id}: {res.status_notes}"
        assert res.schedule_e1_check_passed is True


def test_full_50_case_benchmark_execution():
    """Execute the complete 50-case benchmark harness and verify 100% pass rate."""
    report = run_full_50_case_benchmark()
    assert report.total_cases == 50
    assert report.failed_cases == 0
    assert report.passed_cases == 50
    assert report.pass_rate_percentage == 100.0
    assert report.lethal_mimic_ruleout_rate == 100.0
    assert report.pregnancy_teratogen_blockade_rate == 100.0
    assert report.schedule_e1_poison_lock_rate == 100.0
    assert report.ama_agni_gating_rate == 100.0
    assert report.pediatric_clamping_rate == 100.0
