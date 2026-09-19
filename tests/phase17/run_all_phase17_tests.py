"""Automated Verification Master Test Runner for Phase 17.

Phase 17 Deliverables:
- Classical Formulation Architecture (Bhaishajya Kalpana) Knowledge Graph (15+ Classical Formulations)
- Kalpana Form Classifications & Shelf-life Standards (AFI/API)
- Sneha Paka Stage Determinations & Usage Clinical Rules
- Anupana Carrier Matrix (8 Classical Vehicles) with Bioavailability Enhancement Factors
- Classical Viruddha Ahara Firewalls (1:1 Honey-Ghee lethal toxicity, heated honey Ama-Visha)
- Polyherbal Synergy & Doshic Vector Calculus Engine
- Full RESTful API for Formulations, Detail, Anupana, and Synergy Evaluation
- Complete Database Persistence and SQLite WAL Integration
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 17 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 17 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Classical Formulation Architecture (Bhaishajya Kalpana) & Polyherbal Synergy Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_bhaishajya_kalpana_engine.py"),
        str(Path(__file__).parent / "test_bhaishajya_kalpana_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 17 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 17 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
