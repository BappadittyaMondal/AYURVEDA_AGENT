"""
AYURVEDA_AGENT :: Phase 34 Automated Test Suite Runner
======================================================
Runs all unit and integration tests for Paschat Karma, Samsarjana Krama & Longitudinal EHR Persistence.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 34 AUTOMATED TEST RUNNER")
    print("Scope: Paschat Karma, Samsarjana Krama & Longitudinal EHR Persistence Store")
    print("=" * 80)

    exit_code = pytest.main([
        "-v",
        "tests/phase34/test_paschat_karma_engine.py",
        "tests/phase34/test_paschat_karma_api.py"
    ])

    print("=" * 80)
    if exit_code == 0:
        print(">>> PHASE 34 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 34 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    sys.exit(exit_code)
