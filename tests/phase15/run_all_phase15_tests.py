"""Automated Verification Master Test Runner for Phase 15.

Phase 15 Deliverables:
- Ashtodara Shata Classical Disease Taxonomy (20+ Core Entities)
- Morbidity Dual-Coding Engine (AYUSH NAMASTE, WHO ICD-11 TM2, ICD-11 Biomed, ICD-10)
- ABDM / HL7 FHIR Condition Resource Synthesis with Multi-Terminology Coding
- Patient Diagnosis Ledger with Verification Statuses
- Full RESTful API with Search, Detail, Diagnosis Recording, and FHIR Bundle Exporter
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
    """Execute all Phase 15 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 15 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Classical Disease Classification & ICD-11 / NAMASTE Morbidity Mapping Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_morbidity_coding_engine.py"),
        str(Path(__file__).parent / "test_morbidity_coding_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 15 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 15 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
