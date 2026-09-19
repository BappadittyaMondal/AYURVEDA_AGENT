"""Automated Verification Master Test Runner for Phase 19.

Phase 19 Deliverables:
- Clinical Panchakarma Protocol Architecture (Vamana, Virechana, Basti, Nasya, Raktamokshana)
- Phase 09 Ama Gating Firewall Integration (AGI < 1.80 mandatory before Shodhana)
- Purva Karma Snehana & Swedana Verification Engine
- Real-Time Bedside Vega Logging & Vitals Monitoring
- Chaturvidha Shuddhi Pariksha (Vaigiki, Maniki, Antiki, Laingiki)
- Terminal Milestone Detection (Pittanta for Vamana, Kaphanta for Virechana)
- Atiyoga Complication Detection & Emergency Stambhana Protocol Triggers
- Samsarjana Krama Graduated Dietetics Generator (Pravara 7-day, Madhyama 5-day, Avara 3-day)
- Full RESTful API with Plan Management, Vega Logging, and Shuddhi Evaluation
- Complete SQLite WAL Persistence with Indexed Queries
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 19 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 19 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Clinical Panchakarma Protocol Engine & Bedside Vega Tracking")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_panchakarma_engine.py"),
        str(Path(__file__).parent / "test_panchakarma_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 19 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 19 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
