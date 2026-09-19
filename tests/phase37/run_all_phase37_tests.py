"""
AYURVEDA_AGENT :: Phase 37 Automated Test Suite Runner
======================================================
Runs all unit and integration tests for Multi-Lingual Regional Translation & Voice Intake.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 37 AUTOMATED TEST RUNNER")
    print("Scope: Multi-Lingual Regional Translation & Voice-to-EHR Audio Intake (12 Indian Languages)")
    print("=" * 80)

    exit_code = pytest.main([
        "-v",
        "tests/phase37/test_multilingual_engine.py",
        "tests/phase37/test_multilingual_api.py"
    ])

    print("=" * 80)
    if exit_code == 0:
        print(">>> PHASE 37 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 37 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    sys.exit(exit_code)
