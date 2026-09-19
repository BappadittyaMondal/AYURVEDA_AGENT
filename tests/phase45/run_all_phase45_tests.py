"""
tests/phase45/run_all_phase45_tests.py - Test runner for Phase 45.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 45 AUTOMATED TEST RUNNER")
    print("Scope: Evidence-Based Clinical Trial Registry & Integrative Research (CTRI Bridging)")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase45/test_clinical_trials_engine.py",
        "tests/phase45/test_clinical_trials_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 45 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 45 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
