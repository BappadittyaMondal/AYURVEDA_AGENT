"""Automated Verification Master Test Runner for Phase 13.

Phase 13 Deliverables:
- Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine)
- Trividha Host Vitality & Dhatu Sarata Synthesis (B_rogi Metric)
- Multi-dimensional Disease Virulence Synthesis (B_roga Metric)
- Bi-directional Ratio (R_BR) & Differential Formulation
- Panchakarma Bio-purification Eligibility Firewall (Frail host protection)
- Dynamic Dosage Scalar (lambda_dose in [0.25, 1.5])
- SQLite WAL Persistence with Immutable Audit Trail & Test Coverage
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 13 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 13 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_roga_rogi_bala_engine.py"),
        str(Path(__file__).parent / "test_roga_rogi_bala_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 13 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 13 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
