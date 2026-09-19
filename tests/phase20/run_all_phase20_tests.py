"""Automated Verification Master Test Runner for Phase 20.

Phase 20 Deliverables:
- Upakarma & Bahya Parimarjana Therapy Knowledge Matrix (12 Classical Modalities)
- Thermodynamic Temperature Boundaries & Maximum Safe Burn Limits
- Hydrokinetic Flow Dynamics (Shirodhara / Takradhara Height & Flow Rate)
- Lepa Layer Thickness & Desiccation Timing Standards
- Pre-Session Clinical Screening Engine (Contraindication & Ama Status Cross-Referencing)
- Full RESTful API for Therapies Catalog, Screening, and Session History
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
    """Execute all Phase 20 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 20 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Upakarma & Bahya Parimarjana Therapy Matrix (Thermodynamics & Kinetics)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_upakarma_engine.py"),
        str(Path(__file__).parent / "test_upakarma_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 20 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 20 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
