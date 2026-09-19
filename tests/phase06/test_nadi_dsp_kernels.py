"""Phase 06: Test Suite for Nadi Waveform DSP Filtering, FFT Decomposition & Synthesis."""
import numpy as np
import pytest
from core.nadi_dsp import (
    compute_heart_rate_and_dpdt,
    compute_spectral_bands,
    decompose_nadi_waveform,
    filter_nadi_signal,
    generate_synthetic_nadi,
)
from models.nadi import NadiGatiType


def test_bandpass_filter_attenuation():
    """Verify that Butterworth bandpass filter suppresses DC drift and ultra-high frequency noise."""
    fs = 250.0
    t = np.linspace(0, 2.0, int(2 * fs), endpoint=False)

    # Signal = Constant DC (5.0) + Target In-band component (3.0 Hz, amp 1.0) + High freq noise (60 Hz, amp 1.0)
    raw = 5.0 + np.sin(2 * np.pi * 3.0 * t) + np.sin(2 * np.pi * 60.0 * t)

    filtered = filter_nadi_signal(raw, fs=fs, lowcut=0.5, highcut=20.0)

    # 1. DC offset eliminated
    assert abs(np.mean(filtered)) < 0.1, f"Expected zero-mean after filter, got {np.mean(filtered)}"

    # 2. Total variance significantly reduced (60Hz noise stripped)
    assert np.std(filtered) < np.std(raw)


def test_fft_spectral_band_separation():
    """Verify that pure tones concentrate power exclusively in their respective Doshic bands."""
    fs = 250.0
    t = np.linspace(0, 4.0, int(4 * fs), endpoint=False)

    # 1. Pure Kapha tone (1.0 Hz)
    sig_k = np.sin(2 * np.pi * 1.0 * t)
    p_k, p_p, p_v, _ = compute_spectral_bands(sig_k, fs=fs)
    assert p_k > p_p and p_k > p_v

    # 2. Pure Pitta tone (3.0 Hz)
    sig_p = np.sin(2 * np.pi * 3.0 * t)
    p_k, p_p, p_v, _ = compute_spectral_bands(sig_p, fs=fs)
    assert p_p > p_k and p_p > p_v

    # 3. Pure Vata tone (6.0 Hz)
    sig_v = np.sin(2 * np.pi * 6.0 * t)
    p_k, p_p, p_v, _ = compute_spectral_bands(sig_v, fs=fs)
    assert p_v > p_k and p_v > p_p


def test_synthetic_nadi_waveform_generation_and_classification():
    """Verify that synthetic Sarpa, Manduka, and Hamsa waveforms decompose into correct primary Gati."""
    fs = 250.0

    # 1. Sarpa (Vata)
    sarpa_samples = generate_synthetic_nadi(NadiGatiType.SARPA, duration_sec=4.0, fs=fs, noise_level=0.01)
    res_sarpa = decompose_nadi_waveform(sarpa_samples, fs=fs)
    assert res_sarpa["primary_gati"] == NadiGatiType.SARPA
    assert res_sarpa["doshic_weights"]["vata"] > 0.45

    # 2. Manduka (Pitta)
    manduka_samples = generate_synthetic_nadi(NadiGatiType.MANDUKA, duration_sec=4.0, fs=fs, noise_level=0.01)
    res_manduka = decompose_nadi_waveform(manduka_samples, fs=fs)
    assert res_manduka["primary_gati"] == NadiGatiType.MANDUKA
    assert res_manduka["doshic_weights"]["pitta"] > 0.45

    # 3. Hamsa (Kapha)
    hamsa_samples = generate_synthetic_nadi(NadiGatiType.HAMSA, duration_sec=4.0, fs=fs, noise_level=0.01)
    res_hamsa = decompose_nadi_waveform(hamsa_samples, fs=fs)
    assert res_hamsa["primary_gati"] == NadiGatiType.HAMSA
    assert res_hamsa["doshic_weights"]["kapha"] > 0.45


def test_heart_rate_and_dpdt_metrics():
    """Verify accurate extraction of physiological heart rate and systolic velocity slope."""
    fs = 250.0
    # Create 1.2 Hz pulse (72 bpm)
    t = np.linspace(0, 5.0, int(5 * fs), endpoint=False)
    sig = np.sin(2 * np.pi * 1.2 * t)

    hr, dpdt = compute_heart_rate_and_dpdt(sig, fs=fs)
    assert 68.0 <= hr <= 76.0, f"Expected ~72 bpm, got {hr}"
    assert dpdt > 0.0
