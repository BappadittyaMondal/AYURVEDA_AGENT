"""Automated Verification Master Test Runner for Phase 33.

Phase 33 Deliverables:
- 12 Classical Leeches Taxonomy (6 Nirvisha & 6 Savisha) with Morphology and Salivary Pharmacology
- Bio-active Salivary Pharmacology Mapping (Hirudin, Calin, Bdellin, Eglin, Hyaluronidase, Destabilase)
- Siravedha Anatomical Vein Selection Matrix & 98 Avadhya Siras (prohibited veins) Firewall
- Raktamokshana Blood Volume Permissible Limits by Rogi Bala & Season (Sushruta Sutrasthana Ch. 14)
- Severe Anemia, Moderate Anemia, Coagulopathy, and Hemodynamic Shock Safety Firewalls
- Full RESTful API for Jalauka Catalog, Siravedha Matrix, Safety Auditing, and Procedure Logging
- Database Persistence in Tables 70, 71, 72 with Fast Query Indexes
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 33 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 33 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Jalaukavacharana, Siravedha & Raktamokshana Biotherapy Suite")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_raktamokshana_engine.py"),
        str(Path(__file__).parent / "test_raktamokshana_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 33 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 33 VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
