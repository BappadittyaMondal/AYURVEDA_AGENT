"""Automated Verification Master Test Runner for Phase 02.

Phase 02 Deliverables:
- NCISM Practitioner Credentialing & Registration
- Master Patient Index (MPI) with 14-Digit ABHA ID Binding
- Prakriti Diagnostic Engine on 2-Simplex Vector Space
- 30-Parameter Sharirika & Manasika Clinical Questionnaire Matrix
- Multi-Hospital Tenant Isolation
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 02 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 02 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: NCISM Practitioner Credentialing, MPI with ABHA & Prakriti Simplex Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_practitioner_credentialing.py"),
        str(Path(__file__).parent / "test_mpi_abha.py"),
        str(Path(__file__).parent / "test_prakriti_simplex.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 02 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 02 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
