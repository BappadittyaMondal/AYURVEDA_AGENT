"""
tests/phase39/run_all_phase39_tests.py - Test runner for Phase 39.
"""

import sys
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 39 AUTOMATED TEST RUNNER")
    print("Scope: Classical Pulse Sensor & Wearable IoT Hardware Interface")
    print("=" * 80)

    exit_code = pytest.main([
        "tests/phase39/test_iot_sensors_engine.py",
        "tests/phase39/test_iot_sensors_api.py",
        "-v"
    ])

    if exit_code == 0:
        print("=" * 80)
        print(">>> PHASE 39 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f">>> PHASE 39 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
        print("=" * 80)

    sys.exit(exit_code)
