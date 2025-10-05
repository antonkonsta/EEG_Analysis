"""
Plotting utilities for EEG data visualization.

This module contains functions for creating time domain and frequency domain plots.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from .signal_analysis import calculate_ac_pk_to_pk, calculate_dc_drift


def plot_time_domain(ax, data, channel_name, sampling_rate=1000.0):
    """Plot time domain signal for a channel"""
    time = np.arange(len(data)) / sampling_rate
    ax.plot(time, data, 'b-', linewidth=0.5, label='Raw Signal')
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Amplitude (V)')
    ax.set_title(f'{channel_name} - Time Domain')
    ax.grid(True, alpha=0.3)
    
    # Calculate average amplitude with visualization info
    ac_pk_pk, filtered_data, best_window = calculate_ac_pk_to_pk(data, sampling_rate)
    
    # Calculate and plot DC drift
    dc_drift_signal, drift_range, min_drift_idx, max_drift_idx = calculate_dc_drift(data, sampling_rate)
    ax.plot(time, dc_drift_signal, 'orange', linewidth=2, alpha=0.8, label='DC Drift')
    
    # Mark the highest and lowest DC drift points
    ax.plot(time[max_drift_idx], dc_drift_signal[max_drift_idx], 'ro', markersize=6, 
            markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=1)
    ax.plot(time[min_drift_idx], dc_drift_signal[min_drift_idx], 'ro', markersize=6, 
            markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=1)
    
    # Add annotations for drift points
    ax.annotate(f'Max: {dc_drift_signal[max_drift_idx]*1000:.1f}mV', 
                xy=(time[max_drift_idx], dc_drift_signal[max_drift_idx]),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                fontsize=7)
    ax.annotate(f'Min: {dc_drift_signal[min_drift_idx]*1000:.1f}mV', 
                xy=(time[min_drift_idx], dc_drift_signal[min_drift_idx]),
                xytext=(10, -20), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                fontsize=7)
    
    # Scale y-axis to signal range with small padding
    y_min, y_max = np.min(data), np.max(data)
    y_range = y_max - y_min
    padding = y_range * 0.05  # 5% padding
    ax.set_ylim(y_min - padding, y_max + padding)
    
    # Add visual indicator for the amplitude measurement in the best representative window
    if best_window:
        start_idx = best_window['start_idx']
        end_idx = best_window['end_idx']
        
        # Get the window data from original signal for visualization
        window_data = data[start_idx:end_idx]
        window_time = time[start_idx:end_idx]
        
        # Calculate the theoretical amplitude thresholds based on our calculated value
        calculated_amplitude = ac_pk_pk  # This is our calculated average amplitude
        data_median = np.median(window_data)  # Center point of the signal
        upper_threshold = data_median + calculated_amplitude / 2
        lower_threshold = data_median - calculated_amplitude / 2
        
        # Find actual peaks and troughs that are closest to our calculated thresholds
        # Find points near the upper threshold
        upper_candidates = []
        lower_candidates = []
        
        for i, (t, val) in enumerate(zip(window_time, window_data)):
            if val >= upper_threshold * 0.95:  # Within 5% of upper threshold
                upper_candidates.append((i, t, val))
            if val <= lower_threshold * 1.05:  # Within 5% of lower threshold  
                lower_candidates.append((i, t, val))
        
        # Select the best peak and trough (closest to thresholds)
        if upper_candidates and lower_candidates:
            # Find the upper point closest to our upper threshold
            best_upper = min(upper_candidates, key=lambda x: abs(x[2] - upper_threshold))
            # Find the lower point closest to our lower threshold  
            best_lower = min(lower_candidates, key=lambda x: abs(x[2] - lower_threshold))
            
            peak_time = best_upper[1]
            peak_val = best_upper[2]
            trough_time = best_lower[1]
            trough_val = best_lower[2]
            
            # Draw horizontal lines from peak and trough to the y-axis (left side)
            x_left = ax.get_xlim()[0]  # Leftmost x position
            
            # Lines from points to y-axis
            ax.plot([peak_time, x_left], [peak_val, peak_val], 'r--', linewidth=1.5, alpha=0.6)
            ax.plot([trough_time, x_left], [trough_val, trough_val], 'r--', linewidth=1.5, alpha=0.6)
            
            # Add value labels on the y-axis at the left edge
            ax.text(x_left - (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02, peak_val, 
                   f'{peak_val*1000:.1f}mV', ha='right', va='center', 
                   color='red', fontweight='bold', fontsize=8)
            ax.text(x_left - (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02, trough_val, 
                   f'{trough_val*1000:.1f}mV', ha='right', va='center', 
                   color='red', fontweight='bold', fontsize=8)
            
            # Add small markers at the actual points
            ax.plot(peak_time, peak_val, 'ro', markersize=4, alpha=0.8)
            ax.plot(trough_time, trough_val, 'ro', markersize=4, alpha=0.8)
    
    # Add legend
    ax.legend(loc='upper right', fontsize=8)
    
    # Add average amplitude measurement as text box (top left)
    ax.text(0.02, 0.98, f'Avg Amplitude: {ac_pk_pk*1000:.1f} mV', 
            transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.8),
            fontsize=9, fontweight='bold')
    
    # Add DC drift range measurement as text box (bottom left)
    ax.text(0.02, 0.02, f'DC Drift: {drift_range*1000:.1f} mV', 
            transform=ax.transAxes, verticalalignment='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8),
            fontsize=9, fontweight='bold')


def plot_fft(ax, data, channel_name, sampling_rate=1000.0):
    """Plot FFT spectrum for a channel"""
    # Compute power spectral density using Welch's method
    freqs, psd = welch(data, fs=sampling_rate, nperseg=2048)
    
    # Plot only up to 100 Hz for EEG relevance
    mask = freqs <= 100
    freqs = freqs[mask]
    psd = psd[mask]
    
    ax.semilogy(freqs, psd, 'r-', linewidth=1)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Power Spectral Density (V²/Hz)')
    ax.set_title(f'{channel_name} - Frequency Domain (FFT)')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Add alpha band highlighting
    ax.axvline(x=8, color='green', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvline(x=12, color='green', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvspan(8, 12, alpha=0.1, color='green')


def plot_fft_high_accuracy(ax, data, channel_name, sampling_rate=1000.0):
    """Plot high-accuracy FFT spectrum for a channel"""
    data_length = len(data)
    
    # Choose nperseg based on data length for best accuracy
    nperseg = min(max(data_length // 8, 1024), 8192)
    
    # Use Welch's method with optimal parameters
    freqs, psd = welch(
        data, 
        fs=sampling_rate, 
        window='hann',          
        nperseg=nperseg,        
        noverlap=nperseg//2,    
        nfft=nperseg*2,         
        detrend='linear',       
        scaling='density'       
    )
    
    # Plot only up to 100 Hz for EEG relevance
    mask = freqs <= 100
    freqs = freqs[mask]
    psd = psd[mask]
    
    ax.semilogy(freqs, psd, 'r-', linewidth=1)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Power Spectral Density (V²/Hz)')
    ax.set_title(f'{channel_name} - Frequency Domain (High-Accuracy FFT)')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Add alpha band highlighting
    ax.axvline(x=8, color='green', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvline(x=12, color='green', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvspan(8, 12, alpha=0.1, color='green')