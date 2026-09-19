"""Automated Verification Master Test Runner for Phase 05.

Phase 05 Deliverables:
- Dashavidha Pariksha 10-Fold Systemic Clinical Evaluation Engine
- Rogi Bala (Host Vitality) Quantitative Valuation Matrix
- Roga Bala (Disease Virulence) Multidimensional Penetration Metric
- Rogi-Roga Bala Valuation Ratio (R_BR) & Therapeutic Intensity Eligibility
- SQLite WAL Persistence & Longitudinal Valuation Trajectory
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 05 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 05 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Dashavidha Pariksha Diagnostics & Rogi-Roga Bala Valuation Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_dashavidha_valuation.py"),
        str(Path(__file__).parent / "test_dashavidha_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 05 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 05 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
