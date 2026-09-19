"""Automated Verification Master Test Runner for Phase 08.

Phase 08 Deliverables:
- Jihwa Pariksha Computer Vision & Micro-Colorimetry Tongue Coating Analysis
- sRGB to D65 CIE-L*a*b* Color Space Transformation
- Coating Area Ratio (CAR) & Depth Stratification (None, Thin, Moderate, Thick)
- Chromatic Phenotype Extraction (Shweta, Peeta, Krishna/Shyama, Rakta, Prakrita Pink)
- Somatotopic Mapping (Root/Pakvashaya, Center/Amashaya-Agni, Tip/Circulation)
- Quantitative Ama Scoring & Sama/Nirama Gating
- Simplex Barycentric Doshic Vector Projection with Dirichlet Smoothing
- Synthetic Lingual Parameter Synthesis & Persistence with Audit Ledger
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 08 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 08 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Jihwa Pariksha Computer Vision & Micro-Colorimetry Tongue Analysis")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_jihwa_colorimetry.py"),
        str(Path(__file__).parent / "test_jihwa_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 08 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 08 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
