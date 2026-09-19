"""Automated Verification Master Test Runner for Phase 03.

Phase 03 Deliverables:
- Dynamic Vikriti Assessment on 2-Simplex Vector Space
- Kullback-Leibler (KL) Information Divergence Engine
- Mahalanobis Distance Metric on 2D Projected Simplex Subspace
- Vikriti Severity Index (VSI) Scoring & Tier Classification
- Directional Doshic Deviations (Vriddhi, Kshaya, Sama)
- Longitudinal Vikriti Historical Tracking & Telemetry
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 03 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 03 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Vikriti Dynamic Diagnostic Engine & VSI Vector Analytics")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_vikriti_mathematics.py"),
        str(Path(__file__).parent / "test_vikriti_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 03 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 03 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
