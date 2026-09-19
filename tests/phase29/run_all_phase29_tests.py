"""Automated Verification Master Test Runner for Phase 29.

Phase 29 Deliverables:
- Classical Rasayana Protocols Catalog (Kamya, Naimittika, Ajasrika, Medhya, Achara)
- Ojas Reserve, Vyadhikshamatwa & Biological Ageing Calculus (Ojo Visramsa, Vyapat, Kshaya)
- Decadal Loss of Attributes Progression (Sharngadhara Samhita Purva Khanda 6/19)
- Charakokta Chatush-Medhya Rasayana Cognitive Protocol
- Intensive Kuti Praveshika Screening & Safety Firewall (Trigarbha Architecture)
- Full RESTful API for Protocols, Ojas Evaluations, and Kuti Praveshika Admissions
- SQLite WAL Persistence with Hash-Chained Audit Ledger Logging
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 29 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 29 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Rasayana Tantra, Jara Chikitsa & Longevity Medicine Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_rasayana_tantra_engine.py"),
        str(Path(__file__).parent / "test_rasayana_tantra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 29 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 29 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
