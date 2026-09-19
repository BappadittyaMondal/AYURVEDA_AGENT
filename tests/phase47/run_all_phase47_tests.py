"""
tests/phase47/run_all_phase47_tests.py - Test runner for Phase 47.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 47 AUTOMATED TEST RUNNER")
    print("Scope: Outpatient (OPD) Queue Optimization & Token Flow Management")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase47/test_opd_queue_engine.py",
        "tests/phase47/test_opd_queue_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 47 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 47 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
