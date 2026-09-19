"""
tests/phase44/run_all_phase44_tests.py - Test runner for Phase 44.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 44 AUTOMATED TEST RUNNER")
    print("Scope: Pharmacovigilance ADR Reporting Engine (PvPI & NPvCC Gateway)")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase44/test_pharmacovigilance_engine.py",
        "tests/phase44/test_pharmacovigilance_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 44 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 44 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
