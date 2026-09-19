"""Automated Verification Master Test Runner for Phase 01.

Phase 01 Deliverables:
- Core System Scaffolding & Configuration
- SQLite WAL Persistence Kernel & Pragmas
- Zero-Trust RBAC & HS256 Token Authority
- SHA-256 Audit Chaining Ledger
- FastAPI Application Engine & Health API
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 01 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 01 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Core Architecture, Zero-Trust RBAC & SQLite WAL Kernel")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_database_wal.py"),
        str(Path(__file__).parent / "test_zero_trust_rbac.py"),
        str(Path(__file__).parent / "test_health_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 01 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 01 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
