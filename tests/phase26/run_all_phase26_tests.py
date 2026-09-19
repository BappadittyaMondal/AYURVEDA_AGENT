"""Automated Verification Master Test Runner for Phase 26.

Phase 26 Deliverables:
- Garbha Sambhava Samagri (Ritu, Kshetra, Ambu, Beeja) Preconception Fertility Calculus
- Month-by-Month Garbhini Paricharya Regimen (1st through 9th Month)
- Antenatal Consultation with Dauhrida Tracking & High-Risk Obstetric Emergency Triage Firewall
- Classical 20 Yoni Vyapad Gynecological Classification & Dual ICD-11 Mapping
- Yoni Pichu, Uttarabasti, and Formulations Prescribing Engine
- Full RESTful API for Fertility, Garbhini Regimens, Antenatal Care, and Yoni Vyapad
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
    """Execute all Phase 26 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 26 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Prasuti Tantra, Stri Roga & Garbhini Paricharya Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_prasuti_tantra_engine.py"),
        str(Path(__file__).parent / "test_prasuti_tantra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 26 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 26 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
