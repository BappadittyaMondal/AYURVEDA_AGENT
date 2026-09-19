"""Automated Verification Master Test Runner for Phase 10.

Phase 10 Deliverables:
- Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva)
- Ashta Sara Purusha Functional Mapping (Charaka Vimana 8)
- Weighted Overall Sarata Index (OSI) 0-100% Formulation
- Three-Tier Stratification (Pravara, Madhyama, Avara)
- Target Tissue Vulnerability & Kha-vaigunya Risk Identification
- Classical Dhatu-Specific Rasayana Pharmacology & Dietary Directives
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
    """Execute all Phase 10 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 10 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_dhatu_sarata_engine.py"),
        str(Path(__file__).parent / "test_dhatu_sarata_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 10 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 10 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
