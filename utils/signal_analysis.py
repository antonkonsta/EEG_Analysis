"""
Signal analysis utilities for EEG data processing.

This module contains functions for analyzing EEG signals including:
- DC drift calculation
- Alpha band SNR analysis  
- Average amplitude calculation
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.signal import butter, filtfilt, iirnotch


def apply_lowpass_filter(data, cutoff_freq, sampling_rate, order=4):
    """
    Apply a low-pass Butterworth filter to the data.
    
    Args:
        data (array): Input signal data
        cutoff_freq (float): Cutoff frequency in Hz
        sampling_rate (float): Sampling rate in Hz
        order (int): Filter order
        
    Returns:
        array: Filtered signal data
    """
    nyquist = sampling_rate / 2
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    filtered_data = filtfilt(b, a, data)
    return filtered_data


def apply_notch_filter(data, notch_freq, sampling_rate, quality_factor=30):
    """
    Apply a notch filter to remove specific frequency (e.g., 60Hz power line noise).
    
    Args:
        data (array): Input signal data
        notch_freq (float): Frequency to notch out in Hz
        sampling_rate (float): Sampling rate in Hz
        quality_factor (float): Quality factor (higher = narrower notch)
        
    Returns:
        array: Filtered signal data
    """
    b, a = iirnotch(notch_freq, quality_factor, sampling_rate)
    filtered_data = filtfilt(b, a, data)
    return filtered_data


def apply_signal_filtering(df, sampling_rate, lowpass_cutoff=40, notch_freq=60, notch_q=30, 
                          lowpass_enabled=True, notch_enabled=True):
    """
    Apply complete signal filtering pipeline to EEG data.
    
    Args:
        df (DataFrame): EEG data with channels as columns
        sampling_rate (float): Sampling rate in Hz
        lowpass_cutoff (float): Low-pass filter cutoff frequency in Hz
        notch_freq (float): Notch filter frequency in Hz
        notch_q (float): Notch filter quality factor
        lowpass_enabled (bool): Whether to apply low-pass filter
        notch_enabled (bool): Whether to apply notch filter
        
    Returns:
        DataFrame: Filtered EEG data
        dict: Filter specifications used
    """
    filtered_df = df.copy()
    
    # Get numeric columns only (skip time column if present)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    # Build filter description
    filter_parts = []
    if lowpass_enabled:
        filter_parts.append(f"Low-pass: {lowpass_cutoff} Hz")
    if notch_enabled:
        filter_parts.append(f"Notch: {notch_freq} Hz (Q={notch_q})")
    
    if not filter_parts:
        print("No filters enabled - returning original data")
        return filtered_df, {
            'filtered': False,
            'lowpass_enabled': False,
            'notch_enabled': False
        }
    
    print(f"Applying signal filtering to {len(numeric_cols)} channels...")
    print(f"  Filters: {', '.join(filter_parts)}")
    
    for col in numeric_cols:
        filtered_data = df[col].values.copy()
        
        # Apply low-pass filter if enabled
        if lowpass_enabled:
            filtered_data = apply_lowpass_filter(filtered_data, lowpass_cutoff, sampling_rate)
        
        # Apply notch filter if enabled
        if notch_enabled:
            filtered_data = apply_notch_filter(filtered_data, notch_freq, sampling_rate, notch_q)
        
        filtered_df[col] = filtered_data
    
    filter_specs = {
        'filtered': True,
        'lowpass_enabled': lowpass_enabled,
        'notch_enabled': notch_enabled,
        'lowpass_cutoff': lowpass_cutoff,
        'notch_freq': notch_freq,
        'notch_q': notch_q,
        'sampling_rate': sampling_rate
    }
    
    return filtered_df, filter_specs


import numpy as np
from scipy.signal import butter, filtfilt, welch


def calculate_dc_drift(data, sampling_rate=1000.0):
    """
    Calculate DC drift using a simple moving average approach.
    
    Parameters:
        data (array): Time domain signal data
        sampling_rate (float): Sampling rate in Hz
        
    Returns:
        tuple: (dc_drift_signal, drift_range, min_idx, max_idx)
        - dc_drift_signal: array, the smooth DC drift component
        - drift_range: float, total drift range (max - min) in volts
        - min_idx: int, index of minimum drift point
        - max_idx: int, index of maximum drift point
    """
    # Simple approach: just use a low-pass filter to extract the DC component
    nyquist = sampling_rate / 2
    lp_cutoff = 0.1  # Hz - low enough to follow slow drift, high enough to be smooth
    b_lp, a_lp = butter(2, lp_cutoff / nyquist, btype='low')  # Lower order for gentler filtering
    dc_drift_signal = filtfilt(b_lp, a_lp, data)
    
    # Find min and max points of DC drift
    min_idx = np.argmin(dc_drift_signal)
    max_idx = np.argmax(dc_drift_signal)
    drift_range = dc_drift_signal[max_idx] - dc_drift_signal[min_idx]
    
    return dc_drift_signal, drift_range, min_idx, max_idx


def calculate_alpha_band_snr(data, sampling_rate=1000.0, alpha_band=(8, 12), noise_band=(80, 100)):
    """
    Calculate alpha band signal-to-noise ratio by comparing alpha peak to noise floor (80-100 Hz).
    
    Uses the same Welch method as the FFT plots for consistency:
    1. Calculate power spectral density using Welch's method
    2. Find highest value in 8-12 Hz range (alpha peak)
    3. Find mean value in 80-100 Hz range (noise floor)
    4. SNR = alpha peak / noise floor
    
    Parameters:
        data (array): Time domain signal data
        sampling_rate (float): Sampling rate in Hz
        alpha_band (tuple): Frequency range for alpha band (min_freq, max_freq)
        noise_band (tuple): Frequency range for noise floor estimation (min_freq, max_freq)
        
    Returns:
        tuple: (alpha_snr, alpha_peak_freq, alpha_peak_amplitude, noise_floor, freqs, psd)
        - alpha_snr: float, signal-to-noise ratio (alpha peak / noise floor)
        - alpha_peak_freq: float, frequency of peak in alpha band (Hz)  
        - alpha_peak_amplitude: float, peak power spectral density in alpha band (V²/Hz) 
        - noise_floor: float, mean power spectral density in noise band (V²/Hz)
        - freqs: array, frequency values for plotting
        - psd: array, power spectral density for plotting
    """
    # Use same parameters as the FFT plot function for consistency
    data_length = len(data)
    nperseg = min(max(data_length // 8, 1024), 8192)
    
    # Calculate power spectral density using Welch's method (same as FFT plot)
    freqs, psd = welch(
        data, 
        fs=sampling_rate, 
        window='hann',          
        nperseg=nperseg,        
        noverlap=nperseg//2,    
        nfft=nperseg*2,         
        detrend='linear',       
        scaling='density'       # V²/Hz - same as FFT plot
    )
    
    # Find alpha band indices (8-12 Hz)
    alpha_mask = (freqs >= alpha_band[0]) & (freqs <= alpha_band[1])
    alpha_freqs = freqs[alpha_mask]
    alpha_psd = psd[alpha_mask]
    
    # Find noise band indices (80-100 Hz)
    noise_mask = (freqs >= noise_band[0]) & (freqs <= noise_band[1])
    noise_psd = psd[noise_mask]
    
    if len(alpha_psd) == 0 or len(noise_psd) == 0:
        return 0.0, 0.0, 0.0, 0.0, freqs, psd
    
    # Find highest value in alpha band (8-12 Hz)
    peak_idx = np.argmax(alpha_psd)
    alpha_peak_amplitude = alpha_psd[peak_idx]
    alpha_peak_freq = alpha_freqs[peak_idx]
    
    # Calculate mean value in noise band (80-100 Hz)
    noise_floor = np.mean(noise_psd)
    
    # Calculate SNR (alpha peak / noise floor)
    if noise_floor > 0:
        alpha_snr = alpha_peak_amplitude / noise_floor
    else:
        alpha_snr = 0.0
    
    return alpha_snr, alpha_peak_freq, alpha_peak_amplitude, noise_floor, freqs, psd


def calculate_ac_pk_to_pk(data, sampling_rate=1000.0):
    """
    Calculate robust average amplitude that ignores extreme spikes and handles DC drift.
    Uses high-pass filtering and percentile-based measurements to avoid artifacts.
    
    Parameters:
        data (array): Time domain signal data
        sampling_rate (float): Sampling rate in Hz
        
    Returns:
        tuple: (robust_pk_pk_amplitude, filtered_data, best_window_info)
        - robust_pk_pk_amplitude: float, average signal amplitude in volts
        - filtered_data: array, high-pass filtered data for plotting
        - best_window_info: dict with window details for visualization
    """
    # Step 1: High-pass filter to remove DC drift (0.5 Hz cutoff)
    nyquist = sampling_rate / 2
    hp_cutoff = 0.5  # Hz - removes very slow drift
    b_hp, a_hp = butter(4, hp_cutoff / nyquist, btype='high')
    filtered_data = filtfilt(b_hp, a_hp, data)
    
    # Step 2: Use shorter windows (5 seconds) for better local analysis
    window_size = int(5 * sampling_rate)  # 5 seconds
    
    if len(filtered_data) <= window_size:
        # Short recording - use percentile-based pk-pk to ignore only extreme spikes
        # Use 99.5th - 0.5th percentile to ignore only the most extreme 1% of values
        robust_pk_pk = np.percentile(filtered_data, 99.5) - np.percentile(filtered_data, 0.5)
        # Find best representative section for visualization
        mid_point = len(filtered_data) // 2
        vis_start = max(0, mid_point - window_size//4)  # Quarter window around middle
        vis_end = min(len(filtered_data), vis_start + window_size//2)
        best_window = {
            'start_idx': vis_start,
            'end_idx': vis_end,
            'pk_pk': robust_pk_pk
        }
        return robust_pk_pk, filtered_data, best_window
    
    # Step 3: Calculate robust pk-pk for each window using lighter percentile filtering
    window_pk_pk_values = []
    window_info = []
    
    for i in range(0, len(filtered_data) - window_size + 1, window_size):
        window_data = filtered_data[i:i + window_size]
        # Use 99.5th - 0.5th percentile to ignore only the most extreme 1% of values
        robust_pk_pk = np.percentile(window_data, 99.5) - np.percentile(window_data, 0.5)
        window_pk_pk_values.append(robust_pk_pk)
        window_info.append({
            'start_idx': i,
            'end_idx': i + window_size,
            'pk_pk': robust_pk_pk
        })
    
    # Step 4: Use median of window values
    overall_pk_pk = np.median(window_pk_pk_values)
    
    # Step 5: Find the window that best matches the overall average
    best_window_idx = np.argmin([abs(w['pk_pk'] - overall_pk_pk) for w in window_info])
    best_window = window_info[best_window_idx]
    
    return overall_pk_pk, filtered_data, best_window