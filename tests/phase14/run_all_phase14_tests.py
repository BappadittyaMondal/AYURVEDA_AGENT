"""Automated Verification Master Test Runner for Phase 14.

Phase 14 Deliverables:
- Nidana Panchaka Diagnostic Knowledge Graph (10 Core Disease Archetypes)
- Multi-Axial Overlap & Differential Diagnosis Ranking Engine
- Pratyatma Linga (Hallmark Feature) Detection & Confidence Calibration
- Exclusion Rationale Generator for Competing Differentials
- Upashaya / Anupashaya Therapeutic Diagnostic Trial Verification
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
    """Execute all Phase 14 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 14 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_nidana_panchaka_engine.py"),
        str(Path(__file__).parent / "test_nidana_panchaka_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 14 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 14 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
