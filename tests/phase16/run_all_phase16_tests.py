"""Automated Verification Master Test Runner for Phase 16.

Phase 16 Deliverables:
- Classical Herbology (Dravya Guna) Knowledge Graph (25+ Core Medicinal Plants)
- Comprehensive Rasa-Panchaka Vectors (Rasa, Guna, Veerya, Vipaka, Prabhava, Karma)
- Phytochemical Database Linking Bioactive Metabolites (Withanolides, Curcuminoids, Boswellic Acids, etc.)
- Quantitative Directional Doshic Modulation Vector Engine (Delta v, Delta p, Delta k)
- Multi-Axial Pharmacological Search & Filtration Engine
- Full RESTful API with Herb Catalog, Pharmacodynamics, and Doshic Impact Calculation
- SQLite WAL Persistence with Fast Lookups & Test Coverage
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 16 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 16 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Classical Herbology (Dravya Guna) Knowledge Graph & Phytochemical Database")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_dravyaguna_engine.py"),
        str(Path(__file__).parent / "test_dravyaguna_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 16 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 16 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
