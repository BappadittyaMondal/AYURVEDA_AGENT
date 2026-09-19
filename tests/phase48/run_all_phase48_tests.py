"""
tests/phase48/run_all_phase48_tests.py - Test runner for Phase 48.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 48 AUTOMATED TEST RUNNER")
    print("Scope: Automated Inventory & Pharmacy Dispensation with Jan Aushadhi / IMPCL Barcoding")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase48/test_pharmacy_inventory_engine.py",
        "tests/phase48/test_pharmacy_inventory_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 48 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 48 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
