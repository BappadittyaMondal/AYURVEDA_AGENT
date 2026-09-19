"""
tests/phase40/run_all_phase40_tests.py - Test runner for Phase 40.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 40 AUTOMATED TEST RUNNER")
    print("Scope: Computer Vision Tongue & Eye Optical Diagnostics Pipeline")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase40/test_vision_diagnostics_engine.py",
        "tests/phase40/test_vision_diagnostics_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 40 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 40 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
