"""Automated Verification Master Test Runner for Phase 21.

Phase 21 Deliverables:
- Classical Ahara Varga Knowledge Graph (24+ food ingredients across 12 classical food groups)
- Disease-Specific Pathya & Apathya Registry (Amavata, Sandhigata Vata, Prameha, Amlapitta)
- 18-Fold Viruddha Ahara Incompatibility Audit Engine (Veerya, Matra, Samskara, Kala, Samyoga)
- Caloric, Macronutrient, and Composite Doshic Vector Calculus
- Full RESTful API for Food Ingredients, Pathya-Apathya, Audits, and Prescriptions
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
    """Execute all Phase 21 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 21 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Clinical Dietetics, Ahara Varga & 18-Fold Viruddha Ahara Expert System")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_dietetics_engine.py"),
        str(Path(__file__).parent / "test_dietetics_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 21 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 21 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
