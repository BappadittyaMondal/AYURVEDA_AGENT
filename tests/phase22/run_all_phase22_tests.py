"""Automated Verification Master Test Runner for Phase 22.

Phase 22 Deliverables:
- Classical Dinacharya Protocol Knowledge Matrix (12 Canonical Regimen Steps)
- Circadian Doshic Bio-Rhythm Clock (Kapha, Pitta, Vata Cycles & Peak Activities)
- Lifestyle Routine Compliance Audit Engine (Circadian Alignment & Corrective Guidance)
- 13 Non-Suppressible Natural Urges (Adharaniya Vegas) & Secondary Udavarta Pathology
- Ritucharya 6-Season Calendar, 14-Day Ritusandhi Firewall & Seasonal Shodhana Windows
- Full RESTful API for Clock, Audits, Natural Urges, and Seasonal Calendars
- SQLite WAL Persistence with Indexed Queries
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 22 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 22 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Dinacharya, Ritucharya & Swasthavritta Lifestyle Optimization Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_swasthavritta_engine.py"),
        str(Path(__file__).parent / "test_swasthavritta_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 22 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 22 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
