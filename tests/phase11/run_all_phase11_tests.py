"""Automated Verification Master Test Runner for Phase 11.

Phase 11 Deliverables:
- Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels)
- Chaturvidha Srotodushti Pattern Extraction (Ati-pravritti, Sanga, Sira-granthi, Vimarga-gamana)
- Mula Sthana Root Origin Mapping (Charaka Vimana 5 & Sushruta Sharira 9)
- Channel Involvement Index Formulation (SII_k)
- Pre-existing Defect & Khavaigunya Susceptibility Detection
- Classical Srotoshodhana Clearing Directives & Formulations
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
    """Execute all Phase 11 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 11 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_srotas_matrix.py"),
        str(Path(__file__).parent / "test_srotas_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 11 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 11 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
