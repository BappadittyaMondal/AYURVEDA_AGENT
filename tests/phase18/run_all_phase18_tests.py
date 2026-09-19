"""Automated Verification Master Test Runner for Phase 18.

Phase 18 Deliverables:
- Classical Mineral & Herbo-Mineral Knowledge Graph (18 Master Minerals across Maharasa, Uparasa, Sadharana Rasa, Dhatu, and Visha)
- Classical Shodhana (Purification & Detoxification) Protocol Engine
- Schedule E(1) Statutory Gating Firewall (blocking unpurified poisons)
- Classical Bhasma Pariksha Engine (7 Nanoscale Verification Tests: Varitara, Unama, Rekhapurna, Apunarbhava, Niruttha, Nis-svadu, Nischandrika)
- Puta (Calcination) Furnace Standards and Cycle Adequacy
- AAS / ICP-MS Elemental Contaminant Limits (AFI/AYUSH Standards: Pb <= 10 ppm, As <= 3 ppm, Cd <= 0.3 ppm, Hg <= 1 ppm)
- Particle Size Distribution Analysis (D50 <= 5um, D90 <= 15um, Nanoscale fraction >= 15%)
- Permitted Daily Exposure (PDE) & Cumulative Heavy Metal Intake Calculus
- Full RESTful API with Mineral Catalog, Shodhana Verification, Bhasma Batch Release, and Safety Exposure Checks
- SQLite WAL Persistence with Indexed Retrieval
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 18 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 18 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Rasa Shastra & Herbo-Mineral Processing Safety Engine (AFI/ICP-MS/AAS)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_rasa_shastra_engine.py"),
        str(Path(__file__).parent / "test_rasa_shastra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 18 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 18 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
