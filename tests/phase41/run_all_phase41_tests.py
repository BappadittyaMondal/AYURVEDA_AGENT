"""
tests/phase41/run_all_phase41_tests.py - Test runner for Phase 41.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 41 AUTOMATED TEST RUNNER")
    print("Scope: Patient Portal & Progressive Web App (PWA) Client Interface")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase41/test_patient_portal_engine.py",
        "tests/phase41/test_patient_portal_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 41 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 41 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
