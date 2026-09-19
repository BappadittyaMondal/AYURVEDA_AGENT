"""
AYURVEDA_AGENT :: Phase 36 Automated Test Suite Runner
======================================================
Runs all unit and integration tests for Real-Time Herb-Drug Interaction (HDI) Matrix.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 36 AUTOMATED TEST RUNNER")
    print("Scope: Real-Time Herb-Drug & Herb-Herb Interaction (HDI/HHI) 28-Point Matrix")
    print("=" * 80)

    exit_code = pytest.main([
        "-v",
        "tests/phase36/test_hdi_matrix_engine.py",
        "tests/phase36/test_hdi_matrix_api.py"
    ])

    print("=" * 80)
    if exit_code == 0:
        print(">>> PHASE 36 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 36 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    sys.exit(exit_code)
