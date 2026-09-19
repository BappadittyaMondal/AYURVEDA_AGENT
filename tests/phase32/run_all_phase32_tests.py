"""Automated Verification Master Test Runner for Phase 32.

Phase 32 Deliverables:
- 101 Classical Yantras & 20 Shastras Structural Registry (Sushruta Sutrasthana Ch. 7 & 8)
- Ashtavidha Shastra Karma Operative Procedures (Chhedana, Bhedana, Lekhana, Vyadhana, etc.)
- Yogya Sutriya Surgical Simulation Competency Certification (Sushruta Sutra 9)
- Kshara-Agni Karma Operative Safety Firewalls & Neutralization Protocols
- Full RESTful API for Surgical Instruments, Operative Procedures, and Yogya Simulations
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
    """Execute all Phase 32 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 32 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative Suite")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_shalya_instruments_engine.py"),
        str(Path(__file__).parent / "test_shalya_instruments_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 32 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 32 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
