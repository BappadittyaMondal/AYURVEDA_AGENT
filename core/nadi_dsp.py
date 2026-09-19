"""Nadi Tarangini Waveform Digital Signal Processing (DSP) & Tri-Doshic Decomposition Kernel."""
import math
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy import signal
from core.prakriti import DIRICHLET_EPSILON
from models.nadi import NadiGatiType, SpectralBandPower


def filter_nadi_signal(
    raw_signal: np.ndarray,
    fs: float = 250.0,
    lowcut: float = 0.5,
    highcut: float = 20.0
) -> np.ndarray:
    """
    Apply zero-phase 4th-order Butterworth bandpass filter to suppress baseline wander and high-frequency noise.
    """
    # Remove DC baseline offset
    detrended = signal.detrend(raw_signal)

    # 4th-order Butterworth bandpass filter
    sos = signal.butter(4, [lowcut, highcut], btype="bandpass", fs=fs, output="sos")
    filtered = signal.sosfiltfilt(sos, detrended)
    return filtered


def compute_spectral_bands(
    filtered_signal: np.ndarray,
    fs: float = 250.0
) -> Tuple[float, float, float, float]:
    """
    Execute real FFT and integrate power spectral density over classical Doshic bands:
    - Kapha Band (Hamsa): [0.5 - 2.0 Hz]
    - Pitta Band (Manduka): [2.0 - 4.5 Hz]
    - Vata Band (Sarpa): [4.5 - 8.0 Hz]
    Returns (kapha_power, pitta_power, vata_power, total_power).
    """
    n = len(filtered_signal)
    fft_vals = np.fft.rfft(filtered_signal)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    psd = (np.abs(fft_vals) ** 2) / n

    # Extract band powers
    mask_kapha = (freqs >= 0.5) & (freqs <= 2.0)
    mask_pitta = (freqs > 2.0) & (freqs <= 4.5)
    mask_vata = (freqs > 4.5) & (freqs <= 8.0)
    mask_total = (freqs >= 0.5) & (freqs <= 8.0)

    p_kapha = float(np.sum(psd[mask_kapha])) if np.any(mask_kapha) else 1e-4
    p_pitta = float(np.sum(psd[mask_pitta])) if np.any(mask_pitta) else 1e-4
    p_vata = float(np.sum(psd[mask_vata])) if np.any(mask_vata) else 1e-4
    p_total = float(np.sum(psd[mask_total])) if np.any(mask_total) else (p_kapha + p_pitta + p_vata)

    return (
        round(p_kapha, 4),
        round(p_pitta, 4),
        round(p_vata, 4),
        round(p_total, 4)
    )


def compute_heart_rate_and_dpdt(
    filtered_signal: np.ndarray,
    fs: float = 250.0
) -> Tuple[float, float]:
    """
    Calculate instantaneous heart rate (bpm) and maximum systolic slope (dP/dt_max).
    """
    # Find systolic percussion peaks (minimum 0.35s distance = max 170 bpm)
    min_distance = int(0.35 * fs)
    peaks, _ = signal.find_peaks(filtered_signal, distance=min_distance, prominence=np.std(filtered_signal) * 0.5)

    if len(peaks) >= 2:
        rr_intervals = np.diff(peaks) / fs
        hr_bpm = 60.0 / float(np.mean(rr_intervals))
    else:
        # Fallback to dominant spectral frequency peak in cardiac range [0.8 - 2.5 Hz]
        n = len(filtered_signal)
        fft_vals = np.fft.rfft(filtered_signal)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        cardiac_mask = (freqs >= 0.8) & (freqs <= 2.5)
        if np.any(cardiac_mask):
            dominant_freq = freqs[cardiac_mask][np.argmax(np.abs(fft_vals[cardiac_mask]))]
            hr_bpm = dominant_freq * 60.0
        else:
            hr_bpm = 72.0

    hr_bpm = max(40.0, min(180.0, round(float(hr_bpm), 1)))

    # Compute maximum pulse slope dP/dt
    dp_dt = np.diff(filtered_signal) * fs
    max_dp_dt = round(float(np.max(dp_dt)), 2) if len(dp_dt) > 0 else 0.0

    return hr_bpm, max_dp_dt


def decompose_nadi_waveform(
    raw_samples: List[float],
    fs: float = 250.0
) -> Dict[str, Any]:
    """
    Full DSP pipeline decomposing radial pulse waveform into Tri-doshic coordinates and dominant Gati.
    """
    arr = np.array(raw_samples, dtype=float)
    filtered = filter_nadi_signal(arr, fs=fs)

    p_k, p_p, p_v, p_tot = compute_spectral_bands(filtered, fs=fs)
    hr_bpm, max_dp_dt = compute_heart_rate_and_dpdt(filtered, fs=fs)

    # Normalize powers onto 2-simplex with Dirichlet smoothing
    eps = DIRICHLET_EPSILON
    sum_powers = p_k + p_p + p_v
    if sum_powers <= 0:
        sum_powers = 1.0

    raw_v = p_v / sum_powers
    raw_p = p_p / sum_powers
    raw_k = p_k / sum_powers

    w_v = (1.0 - 3.0 * eps) * raw_v + eps
    w_p = (1.0 - 3.0 * eps) * raw_p + eps
    w_k = (1.0 - 3.0 * eps) * raw_k + eps

    norm_sum = w_v + w_p + w_k
    w_v = max(round(w_v / norm_sum, 4), eps)
    w_p = max(round(w_p / norm_sum, 4), eps)
    w_k = round(1.0 - (w_v + w_p), 4)

    # Determine dominant classical Gati
    weights = [("SARPA", w_v), ("MANDUKA", w_p), ("HAMSA", w_k)]
    weights.sort(key=lambda x: x[1], reverse=True)

    if weights[0][1] >= 0.45:
        primary_gati = NadiGatiType(weights[0][0])
    else:
        primary_gati = NadiGatiType.SAMANYA

    return {
        "heart_rate_bpm": hr_bpm,
        "max_dp_dt": max_dp_dt,
        "spectral_power": SpectralBandPower(
            kapha_power_0_5_to_2_0_hz=p_k,
            pitta_power_2_0_to_4_5_hz=p_p,
            vata_power_4_5_to_8_0_hz=p_v,
            total_power=p_tot
        ),
        "doshic_weights": {
            "vata": w_v,
            "pitta": w_p,
            "kapha": w_k
        },
        "primary_gati": primary_gati
    }


def generate_synthetic_nadi(
    gati: NadiGatiType,
    duration_sec: float = 4.0,
    fs: float = 250.0,
    noise_level: float = 0.02
) -> List[float]:
    """
    Synthesize physiologically calibrated radial pulse waveforms modeling classical Nadi kinematics.
    """
    n = int(duration_sec * fs)
    t = np.linspace(0, duration_sec, n, endpoint=False)

    if gati == NadiGatiType.SARPA:
        # Vata: High frequency serpentine components (5.5 Hz and 6.8 Hz), heart rate ~88 bpm (1.46 Hz)
        f0 = 1.46
        waveform = (
            0.6 * np.sin(2 * np.pi * f0 * t) +
            0.8 * np.sin(2 * np.pi * 5.5 * t) +
            0.7 * np.sin(2 * np.pi * 6.8 * t + 0.5)
        )
    elif gati == NadiGatiType.MANDUKA:
        # Pitta: Steep dP/dt systolic upslope, prominent percussion peak, energy in [2.5 - 4.0 Hz], HR ~78 bpm (1.30 Hz)
        f0 = 1.30
        waveform = (
            0.9 * np.sin(2 * np.pi * f0 * t) +
            1.2 * np.sin(2 * np.pi * 2.8 * t + 0.3) +
            1.0 * np.sin(2 * np.pi * 3.8 * t + 0.7)
        )
    elif gati == NadiGatiType.HAMSA:
        # Kapha: Slow broad sinusoidal swan gait, dominant in [0.8 - 1.6 Hz], HR ~60 bpm (1.0 Hz)
        f0 = 1.00
        waveform = (
            1.4 * np.sin(2 * np.pi * f0 * t) +
            0.8 * np.sin(2 * np.pi * 1.5 * t + 0.2) +
            0.15 * np.sin(2 * np.pi * 3.0 * t)
        )
    else:  # SAMANYA
        waveform = (
            1.0 * np.sin(2 * np.pi * 1.2 * t) +
            0.5 * np.sin(2 * np.pi * 2.5 * t) +
            0.4 * np.sin(2 * np.pi * 5.0 * t)
        )

    # Add Gaussian noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, n)
        waveform += noise

    return [round(float(x), 4) for x in waveform]
