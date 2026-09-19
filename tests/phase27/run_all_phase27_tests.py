"""Automated Verification Master Test Runner for Phase 27.

Phase 27 Deliverables:
- Kaumarbhritya Developmental Milestones & Classical Samskaras (Jatakarma to Chaula)
- Dual-Posology Pediatric Dosage Scaling (Sharngadhara Ratti, Clark, Cowling)
- Strict Pediatric Toxicology Firewall (Prohibiting Schedule E-1 poisons & heavy metals)
- Kashyapa Classical Bala Roga Syndromes (Phakka, Parigarbhika, Kukunaka, Stanya Dushti)
- Suvarnaprashana Immunomodulation Protocol Engine on Pushya Nakshatra
- Full RESTful API for Milestones, Posology, Consultations, and Suvarnaprashana
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
    """Execute all Phase 27 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 27 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Kaumarbhritya & Bala Roga Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_kaumarbhritya_engine.py"),
        str(Path(__file__).parent / "test_kaumarbhritya_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 27 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 27 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
