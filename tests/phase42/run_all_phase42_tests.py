"""
tests/phase42/run_all_phase42_tests.py - Test runner for Phase 42.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 42 AUTOMATED TEST RUNNER")
    print("Scope: AYUSH GRID Bridge & Zero-Knowledge Verification")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase42/test_ayush_grid_engine.py",
        "tests/phase42/test_ayush_grid_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 42 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 42 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
