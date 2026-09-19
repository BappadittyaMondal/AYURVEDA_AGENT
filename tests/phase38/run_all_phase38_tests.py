"""
AYURVEDA_AGENT :: Phase 38 Automated Test Suite Runner
======================================================
Runs all unit and integration tests for Tele-AYUSH Remote Consultation & e-Prescription.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 38 AUTOMATED TEST RUNNER")
    print("Scope: Tele-AYUSH Remote Consultation, e-Prescription & Video Session Pipeline")
    print("=" * 80)

    exit_code = pytest.main([
        "-v",
        "tests/phase38/test_tele_ayush_engine.py",
        "tests/phase38/test_tele_ayush_api.py"
    ])

    print("=" * 80)
    if exit_code == 0:
        print(">>> PHASE 38 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 38 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    sys.exit(exit_code)
