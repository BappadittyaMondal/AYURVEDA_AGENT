"""
tests/phase43/run_all_phase43_tests.py - Test runner for Phase 43.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 43 AUTOMATED TEST RUNNER")
    print("Scope: Offline-First Edge Node Sync & Rural PHC Resiliency")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase43/test_edge_sync_engine.py",
        "tests/phase43/test_edge_sync_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 43 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 43 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
