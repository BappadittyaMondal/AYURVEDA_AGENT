"""Automated Verification Master Test Runner for Phase 30.

Phase 30 Deliverables:
- The 8 Classical Shukra Dushtis Registry (Ashta Shukra Dushtis per Charaka & Sushruta)
- WHO 6th Edition Semen Analysis Dual-Mapping Diagnostic Engine & Shukra Shuddhi Score
- Classical Klaibya (Male Sexual Dysfunction) 4-Fold Stratification
- Vajikarana Pharmacodynamic Dynamics (Shukra-Janana, Rechaka, Stambhana, Shodhaka)
- Pre-Vajikarana Shodhana Safety Firewall & Eugenics Pathya Protocols
- Full RESTful API for Dushti Registry, Semen Diagnostics, and Vajikarana Prescriptions
- SQLite WAL Persistence with SHA-256 Hash-Chained Audit Ledger Logging
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 30 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 30 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics Engine")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_vajikarana_tantra_engine.py"),
        str(Path(__file__).parent / "test_vajikarana_tantra_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 30 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 30 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
