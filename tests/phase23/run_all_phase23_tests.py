"""Automated Verification Master Test Runner for Phase 23.

Phase 23 Deliverables:
- Classical Manasa Roga Psychiatric Knowledge Matrix (Unmada, Apasmara, Chittodvega, Avasada)
- ICD-11 Dual-Coding Crosswalk for Ayurvedic Psychiatric Diagnoses
- Psychometric Triguna Simplex Vector Calculus (Sattva, Rajas, Tamas)
- Dhi, Dhriti, Smriti Faculty Assessment & Prajnaparadha Index (PPI) Formula
- Psychiatric Crisis Safety Firewall (Suicidal Ideation & Violent Mania Isolation Protocols)
- Comprehensive Trividha Chikitsa Prescribing (Daivavyapashraya, Medhya Rasayanas, Sattvavajaya CBT)
- Full RESTful API for Psychiatric Catalog, Assessments, and Trividha Prescriptions
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
    """Execute all Phase 23 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 23 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Sattvavajaya Chikitsa, Manasa Roga & Mental Health CDSS Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_manasa_roga_engine.py"),
        str(Path(__file__).parent / "test_manasa_roga_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 23 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 23 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
