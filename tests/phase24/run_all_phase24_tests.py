"""Automated Verification Master Test Runner for Phase 24.

Phase 24 Deliverables:
- Classical Marma Sharira Catalog (107 Marmas across 5 prognostic types)
- Pre-Operative Surgical Incision Proximity Screening & Sadyo-Pranahara Shock Firewall
- Agnikarma Thermal Cauterization Delivery Dynamics & Burn Grading Standards
- Ksharasutra Anorectal Seton Tracking & Unit Cutting Time (UCT) Engine
- Vrana Surgical Wound Staging & Shashti-Upakrama Treatment Prescribing
- Full RESTful API for Marmas, Screening, Agnikarma, Ksharasutra, and Wound Care
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
    """Execute all Phase 24 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 24 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Shalya Tantra, Marma Sharira & Agnikarma / Ksharasutra Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_shalya_tantra_engine.py"),
        str(Path(__file__).parent / "test_shalya_tantra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 24 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 24 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
