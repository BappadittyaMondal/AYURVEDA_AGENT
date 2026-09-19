"""Automated Verification Master Test Runner for Phase 25.

Phase 25 Deliverables:
- Classical Shalakya Netra Roga Catalog (76 diseases across 6 Mandalas & 4 Patalas)
- Netra Kriya Kalpa Protocol Engine (Tarpana, Putapaka, Aschyotana, Seka, Pindi, Bidalaka, Anjana)
- Tarpana Retentive Matrakala Calculus & Photoprotective Rest Regimen
- Acute Adhimantha (Angle-Closure Glaucoma Crisis) Emergency Triage Firewall
- ENT Micro-Therapeutics (Karna Purana, Karna Dhoopana, Nasya) & Tympanic Perforation Firewall
- Full RESTful API for Netra Rogas, Tarpana, Ophthalmic Screening, and ENT Procedures
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
    """Execute all Phase 25 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 25 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Shalakya Tantra, Netra Kriya Kalpa & ENT Microsurgical Therapeutics")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_shalakya_tantra_engine.py"),
        str(Path(__file__).parent / "test_shalakya_tantra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 25 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 25 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
