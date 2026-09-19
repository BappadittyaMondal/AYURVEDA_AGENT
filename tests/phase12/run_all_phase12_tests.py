"""Automated Verification Master Test Runner for Phase 12.

Phase 12 Deliverables:
- Shat Kriya Kala Pathological Stage Tracker (6 Stages: Sanchaya, Prakopa, Prasara, Sthanasamshraya, Vyakti, Bheda)
- Pathological Progression Index (PPI) 1.0 - 6.0 Continuous Metric
- Simplex Stage Probability Distribution Formulation on Delta^5
- Prodromal Window (Purvaroopa) & Manifestation (Roopa) Discrimination
- Reversibility Estimation & Prognosis (Sukhasadhya, Krichrasadhya, Yapya, Asadhya)
- Classical Stage-Specific Kriyavidhi Therapeutic Directives
- SQLite WAL Persistence with Audit Ledger & Complete Test Coverage
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 12 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 12 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Shat Kriya Kala Pathological Stage Tracker (6 Stages)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_kriya_kala_engine.py"),
        str(Path(__file__).parent / "test_kriya_kala_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 12 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 12 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
