"""Automated Verification Master Test Runner for Phase 07.

Phase 07 Deliverables:
- Taila Bindu Pariksha Diagnostic & Surface-Tension Fluid Dynamics Simulator
- Harkins Spreading Coefficient Computation
- Ramanujan Elliptic Boundary Geometry & Eccentricity / Circularity Formulation
- Radial Spreading Velocity Kinematics
- Doshic Morphology Inference (Sarpa, Chhatra, Muktakara, Jalavat, Churna, Nimagna)
- Yogaratnakara Prognostic Classification (Sadhya, Krichrasadhya, Asadhya)
- Synthetic Droplet Simulation & Persistence with Audit Ledger
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 07 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 07 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Taila Bindu Pariksha Diagnostic & Surface-Tension Fluid Dynamics")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_taila_bindu_physics.py"),
        str(Path(__file__).parent / "test_taila_bindu_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 07 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 07 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
