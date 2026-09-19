"""
AYURVEDA_AGENT :: Phase 35 Automated Test Suite Runner
======================================================
Runs all unit and integration tests for Western Emergency Break-Glass & Acute Transfer (NABH COP.6).
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 35 AUTOMATED TEST RUNNER")
    print("Scope: Western Emergency Break-Glass & Acute Critical Care Transfer (NABH COP.6)")
    print("=" * 80)

    exit_code = pytest.main([
        "-v",
        "tests/phase35/test_emergency_transfer_engine.py",
        "tests/phase35/test_emergency_transfer_api.py"
    ])

    print("=" * 80)
    if exit_code == 0:
        print(">>> PHASE 35 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 35 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    sys.exit(exit_code)
