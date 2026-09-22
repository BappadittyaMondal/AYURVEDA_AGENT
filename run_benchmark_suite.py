"""
run_benchmark_suite.py - Standalone Clinical Benchmark & Stress Test Runner for AYURVEDA_AGENT.
=============================================================================================
Executes all 50 multi-morbidity patient scenarios across 5 core clinical domains:
1. Kayachikitsa Internal Medicine (10 cases)
2. Emergency Lethal Mimic Rule-Out (10 cases)
3. Vulnerable Cohort & Population Safety (10 cases)
4. Statutory Schedule E(1) Poison Enforcement (10 cases)
5. Shalya, Shalakya, Parasurgical & Marma Triage (10 cases)
"""

import sys
import time
from core.clinical_benchmark_harness import run_full_50_case_benchmark


def main():
    print("=" * 80)
    print("AYURVEDA_AGENT :: 50-CASE MULTI-MORBIDITY CLINICAL BENCHMARK & STRESS HARNESS")
    print("AIIA / AIIMS Clinical Governance & NABH AYUSH Safety Verification Standard")
    print("=" * 80)
    print("Initializing multi-axial clinical engines (Simplex, Ama-Agni, Mimic, Poisons)...")

    report = run_full_50_case_benchmark()

    print("\n" + "-" * 80)
    print(f"{'CASE ID':<10} | {'DOMAIN':<22} | {'TITLE':<32} | {'STATUS':<8}")
    print("-" * 80)

    for r in report.results:
        status_str = "PASSED" if r.passed else "FAILED"
        title_trunc = (r.title[:29] + "...") if len(r.title) > 32 else r.title
        print(f"{r.case_id:<10} | {r.domain:<22} | {title_trunc:<32} | {status_str:<8}")

    print("-" * 80)
    print(f"Total Cases Evaluated:       {report.total_cases}")
    print(f"Total Cases Passed:          {report.passed_cases} / {report.total_cases}")
    print(f"Total Execution Time:        {report.total_duration_seconds} seconds")
    print(f"Overall Clinical Pass Rate:  {report.pass_rate_percentage}%\n")

    print("SAFETY INVARIANT VERIFICATION METRICS:")
    print(f"  1. Lethal Mimic Rule-Out Rate:         {report.lethal_mimic_ruleout_rate}% (100% Zero-Miss Standard)")
    print(f"  2. Pregnancy Teratogen Blockade:       {report.pregnancy_teratogen_blockade_rate}% (100% Zero-Leakage Standard)")
    print(f"  3. Schedule E(1) Poison Interception:  {report.schedule_e1_poison_lock_rate}% (100% Statutory Standard)")
    print(f"  4. Ama-Agni Shodhana Gating Rate:      {report.ama_agni_gating_rate}% (100% Classical Standard)")
    print(f"  5. Pediatric Posology Clamping:        {report.pediatric_clamping_rate}% (100% Overdose Standard)")
    print("=" * 80)

    if report.failed_cases == 0:
        print(">>> 50-CASE BENCHMARK VERIFICATION SUCCESSFUL: 100% PASS RATE (EXIT CODE 0) <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f">>> BENCHMARK VERIFICATION FAILED: {report.failed_cases} FAILURES DETECTED <<<")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
