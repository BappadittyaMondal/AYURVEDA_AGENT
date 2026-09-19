"""
tests/phase46/run_all_phase46_tests.py - Test runner for Phase 46.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 46 AUTOMATED TEST RUNNER")
    print("Scope: High-Volume Inpatient (IPD) Bed Management & Nursing Care Charting")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase46/test_ipd_management_engine.py",
        "tests/phase46/test_ipd_management_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 46 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 46 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
