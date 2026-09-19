"""Automated Verification Master Test Runner for Phase 09.

Phase 09 Deliverables:
- Quantitative Ama Grading Index (AGI) Weighted Scoring Engine
- Ashtanga Hridaya 10 Cardinal Ama Lakshanas Matrix
- Functional Agni Vector Quadruplicate Simplex Decomposition (Samagni, Vishamagni, Tikshnagni, Mandagni)
- Dirichlet Boundary Smoothing on Delta^3
- Panchakarma Shodhana Safety Firewall Gating (Apakva Dosha Protection)
- Clinical Pharmacology & Dietary Therapeutic Directives
- Persistence in SQLite WAL Ledger & Verification
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 09 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 09 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Quantitative Ama Grading Index (AGI) & Agni Vector Gating Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_ama_agni_engine.py"),
        str(Path(__file__).parent / "test_ama_agni_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 09 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 09 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
