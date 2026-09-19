"""Automated Verification Master Test Runner for Phase 06.

Phase 06 Deliverables:
- Nadi Tarangini Waveform Digital Signal Processing (DSP) Engine
- Zero-Phase 4th-Order Butterworth Bandpass Filtering & Detrending
- Fast Fourier Transform (FFT) Sub-band Spectral Power Integration
- Tri-Doshic Orthogonal Waveform Decomposition (Sarpa, Manduka, Hamsa)
- Heart Rate (bpm) and Maximum Systolic Slope (dP/dt_max) Extraction
- Calibrated Synthetic Pulse Telemetry Synthesis & Persistence
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Phase 06 automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: PHASE 06 AUTOMATED VERIFICATION TEST RUNNER")
    print("Scope: Nadi Waveform Signal Processing Engine (Fourier/Wavelet DSP)")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_nadi_dsp_kernels.py"),
        str(Path(__file__).parent / "test_nadi_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> PHASE 06 VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> PHASE 06 VERIFICATION FAILED: EXIT CODE {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
