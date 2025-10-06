#!/usr/bin/env python3
"""
EEG Channel Report Generator

This script generates a PDF report with time domain and FFT plots for each EEG channel.
For each channel, it creates:
1. Time domain plot showing the raw signal
2. FFT plot showing the frequency spectrum

Usage:
    python generate_channel_report.py <csv_file> [output_pdf]
    
Example:
    
    python generate_channel_report.py "data.csv" "my_r        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)t.pdf"
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.signal import welch
import shutil
from datetime import datetime
# Add the parent directory to the path to access utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.channel_utils import load_channel_map, apply_channel_mapping
from utils.signal_analysis import calculate_dc_drift, calculate_alpha_band_snr, calculate_ac_pk_to_pk, apply_signal_filtering
from utils.saturation_analysis import count_saturated_channels_any_point
from utils.plotting_utils import plot_time_domain, plot_fft, plot_fft_high_accuracy
from utils.data_processing import setup_output_folders, move_source_csv, validate_csv_file, get_output_filename, interactive_channel_mapping_selection, interactive_folder_selection, interactive_threshold_selection, interactive_filter_selection, open_pdf_file, clear_screen
from scipy.signal import detrend

def generate_eeg_report(csv_file, output_pdf=None, use_channel_mapping=True, low_thresh=0.053, high_thresh=3.247, percent=0.0, low_amplitude_thresh=0.5, channel_mapping_file=None, custom_folder=None, filter_config=None):
    """
    Generate a PDF report with time and frequency domain plots for each EEG channel
    
    Parameters:
        csv_file (str): Path to the CSV file containing EEG data
        output_pdf (str): Output PDF filename (optional)
        use_channel_mapping (bool): Whether to apply channel mapping
        low_thresh (float): Lower threshold for saturation detection
        high_thresh (float): Upper threshold for saturation detection  
        percent (float): Percentage threshold for considering a channel saturated
    """
    from matplotlib.backends.backend_pdf import PdfPages
    from scipy.signal import welch
    
    # Set default channel mapping file if not provided
    if channel_mapping_file is None:
        script_dir = os.path.dirname(__file__)
        channel_mapping_file = os.path.join(script_dir, '..', 'channel_mappings', 'channel_mappingModified.csv')
    
    # Validate input file and setup output folders
    csv_file = validate_csv_file(csv_file)
    output_paths = setup_output_folders(csv_file, output_pdf, custom_folder)
    output_pdf_path = output_paths['pdf']
    
    print(f"Loading EEG data from: {csv_file}")
    print(f"Report will be saved to: {output_pdf_path}")
    
    # Read the CSV file directly with pandas
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: Could not find file '{csv_file}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Apply channel mapping if requested and if channels are numbered
    if use_channel_mapping:
        try:
            channel_map = load_channel_map(channel_mapping_file)
            # Check if we have numbered channels (Channel 1, Channel 2, etc.)
            if 'Channel 1' in df.columns:
                df = apply_channel_mapping(df, channel_map)
                channel_names = list(channel_map.values())
                print("Applied channel mapping - using anatomical names")
            else:
                # Already has anatomical names
                channel_names = [col for col in df.columns if col != 'Sample Num']
                print("Using existing channel names")
        except Exception as e:
            print(f"Warning: Could not apply channel mapping: {e}")
            channel_names = [col for col in df.columns if col != 'Sample Num']
    else:
        channel_names = [col for col in df.columns if col != 'Sample Num']
    
    # Apply signal filtering if requested
    filter_specs = {'filtered': False}
    if filter_config and filter_config.get('apply_filtering', False):
        try:
            print("\nApplying signal filtering...")
            df, filter_specs = apply_signal_filtering(
                df,
                sampling_rate=filter_config['sampling_rate'],
                lowpass_cutoff=filter_config['lowpass_cutoff'],
                notch_freq=filter_config['notch_freq'],
                notch_q=filter_config['notch_q']
            )
            print("Signal filtering completed successfully.")
        except Exception as e:
            print(f"Warning: Could not apply signal filtering: {e}")
            print("Proceeding with unfiltered data.")
            filter_specs = {'filtered': False}
    else:
        print("Using unfiltered (raw) data.")
    
    # Get sampling rate from filter config or use default
    sampling_rate = filter_specs.get('sampling_rate', 1000.0)
    
    # Perform saturation analysis
    print("Analyzing channel saturation...")
    try:
        num_sat, below_saturated, above_saturated = count_saturated_channels_any_point(
            df, channel_names, low_thresh, high_thresh
        )
        
        # Calculate detailed saturation percentages for each channel
        saturation_details = {}
        for ch in channel_names:
            if ch in df.columns:
                data = df[ch]
                below_pct = (data < low_thresh).mean() * 100
                above_pct = (data > high_thresh).mean() * 100
                saturation_details[ch] = {
                    'below_pct': below_pct,
                    'above_pct': above_pct,
                    'total_sat_pct': max(below_pct, above_pct),
                    'is_saturated': ch in below_saturated or ch in above_saturated
                }
    except Exception as e:
        print(f"Warning: Could not perform saturation analysis: {e}")
        num_sat, below_saturated, above_saturated = 0, [], []
        saturation_details = {}
    
    print(f"Found {len(channel_names)} channels")
    print(f"Saturated channels: {num_sat}")
    print(f"Generating PDF report: {output_pdf_path}")
    
    # Create PDF
    with PdfPages(output_pdf_path) as pdf:
        # Page 1: Title page
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.text(0.5, 0.8, 'EEG Channel Report', fontsize=24, ha='center', weight='bold')
        ax.text(0.5, 0.7, f'Data file: {os.path.basename(csv_file)}', fontsize=14, ha='center')
        ax.text(0.5, 0.65, f'Channels: {len(channel_names)}', fontsize=12, ha='center')
        ax.text(0.5, 0.6, f'Data points: {len(df)}', fontsize=12, ha='center')
        ax.text(0.5, 0.55, f'Duration: {len(df)/1000:.1f} seconds', fontsize=12, ha='center')
        ax.text(0.5, 0.5, f'Saturated channels: {num_sat}', fontsize=12, ha='center', 
                color='red' if num_sat > 0 else 'green')
        
        ax.text(0.5, 0.4, 'Report Contents:', fontsize=14, ha='center', weight='bold')
        ax.text(0.5, 0.36, '1. Methods and settings summary', fontsize=12, ha='center')
        ax.text(0.5, 0.33, '2. EEG performance overview', fontsize=12, ha='center')
        ax.text(0.5, 0.3, '3. All channels overview (time + frequency)', fontsize=12, ha='center')
        ax.text(0.5, 0.27, '4. Average amplitude ranking', fontsize=12, ha='center')
        ax.text(0.5, 0.24, '5. DC drift range ranking', fontsize=12, ha='center')
        ax.text(0.5, 0.21, '6. Alpha band SNR ranking', fontsize=12, ha='center')
        ax.text(0.5, 0.18, '7. Dashboard overview (4x4 panel layouts)', fontsize=12, ha='center')
        ax.text(0.5, 0.15, '8. Channel information table', fontsize=12, ha='center')
        ax.text(0.5, 0.12, '9. Saturation analysis summary', fontsize=12, ha='center')
        ax.text(0.5, 0.09, '10. Individual channel plots', fontsize=12, ha='center')
        
        ax.text(0.5, 0.04, f'Saturation thresholds: <{low_thresh}V or >{high_thresh}V', 
                fontsize=10, ha='center', style='italic')
        ax.text(0.5, 0.01, f'Any point crossing threshold = saturated channel', 
                fontsize=10, ha='center', style='italic')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 2: Methods and Settings Summary
        print("Generating methods and settings summary...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Methods and Settings Summary', fontsize=18, weight='bold', color='navy')
        
        ax = plt.subplot(1, 1, 1)
        ax.axis('off')
        
        y_pos = 0.95
        line_height = 0.025
        section_spacing = 0.04
        
        # Title
        ax.text(0.5, y_pos, 'EEG Analysis Methods and Configuration', 
                fontsize=16, weight='bold', ha='center', transform=ax.transAxes, color='darkblue')
        y_pos -= section_spacing
        
        # Section 1: Saturation Detection
        ax.text(0.05, y_pos, '1. SATURATION DETECTION', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='red')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Low Threshold: {low_thresh}V ({low_thresh*1000:.1f}mV)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'• High Threshold: {high_thresh}V ({high_thresh*1000:.1f}mV)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Method: Any single data point crossing thresholds flags the entire channel', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Purpose: Detect electrode disconnection, impedance issues, or amplifier saturation', 
                fontsize=11, transform=ax.transAxes, style='italic')
        y_pos -= section_spacing
        
        # Section 2: Signal Filtering (if applied)
        if filter_specs.get('filtered', False):
            ax.text(0.05, y_pos, '2. SIGNAL FILTERING', 
                    fontsize=14, weight='bold', transform=ax.transAxes, color='purple')
            y_pos -= line_height
            
            ax.text(0.1, y_pos, f'• Low-pass Filter: {filter_specs["lowpass_cutoff"]}Hz (removes high-frequency noise)', 
                    fontsize=11, transform=ax.transAxes)
            y_pos -= line_height
            ax.text(0.1, y_pos, f'• Notch Filter: {filter_specs["notch_freq"]}Hz (Q={filter_specs["notch_q"]}) - removes power line noise', 
                    fontsize=11, transform=ax.transAxes)
            y_pos -= line_height
            ax.text(0.1, y_pos, f'• Sampling Rate: {filter_specs["sampling_rate"]}Hz', 
                    fontsize=11, transform=ax.transAxes)
            y_pos -= line_height
            ax.text(0.1, y_pos, '• Filter Type: Butterworth low-pass + IIR notch (zero-phase filtfilt)', 
                    fontsize=11, transform=ax.transAxes)
            y_pos -= line_height
            ax.text(0.1, y_pos, '• Purpose: Remove power line interference and high-frequency artifacts', 
                    fontsize=11, transform=ax.transAxes, style='italic')
            y_pos -= section_spacing
            section_num = 3
        else:
            ax.text(0.05, y_pos, '2. SIGNAL FILTERING', 
                    fontsize=14, weight='bold', transform=ax.transAxes, color='gray')
            y_pos -= line_height
            ax.text(0.1, y_pos, '• No filtering applied - using raw EEG data', 
                    fontsize=11, transform=ax.transAxes, color='gray')
            y_pos -= section_spacing
            section_num = 3
        
        # Section 3: Average Amplitude (Low Signal Detection)
        ax.text(0.05, y_pos, f'{section_num}. AVERAGE AMPLITUDE ANALYSIS', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='green')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Low Amplitude Threshold: {low_amplitude_thresh}mV', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Method: High-pass filter (0.5Hz) → 5-second windows → 99.5th-0.5th percentile', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Filtering: Ignores only extreme 1% of data points (spikes/artifacts)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Exemption: Reference channels (containing "REF") excluded from low amplitude criteria', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Purpose: Detect poor electrode contact, high impedance, or weak signal coupling', 
                fontsize=11, transform=ax.transAxes, style='italic')
        y_pos -= section_spacing
        
        # Section 4: DC Drift Analysis
        section_num += 1
        ax.text(0.05, y_pos, f'{section_num}. DC DRIFT ANALYSIS', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='orange')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, '• Low-pass Filter: 0.1Hz cutoff, 2nd order Butterworth', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Method: Extract slow DC component → Find min/max → Calculate range', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Measurement: Total drift range (max - min) over recording period', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Purpose: Assess electrode stability, skin potential changes, amplifier offset drift', 
                fontsize=11, transform=ax.transAxes, style='italic')
        y_pos -= section_spacing
        
        # Section 5: Alpha Band SNR
        section_num += 1
        ax.text(0.05, y_pos, f'{section_num}. ALPHA BAND SNR ANALYSIS', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='purple')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, '• Alpha Band: 8-12 Hz (primary brain rhythm during relaxed wakefulness)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Noise Reference: 80-100 Hz (high-frequency electrical noise)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Method: Welch PSD → Peak alpha power / Mean noise power', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Window Parameters: Hann window, 50% overlap, linear detrend', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Purpose: Quantify signal quality and neurological activity strength vs noise', 
                fontsize=11, transform=ax.transAxes, style='italic')
        y_pos -= section_spacing
        
        # Section 5: Data Processing Pipeline
        ax.text(0.05, y_pos, '5. DATA PROCESSING PIPELINE', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='teal')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, '• Sampling Rate: 1000 Hz (assumed)', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Channel Mapping: Numeric channels → Anatomical electrode names', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Analysis Order: Raw data → Signal filtering (if enabled) → Saturation check → Amplitude analysis → Drift → SNR', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Visual Annotations: Peak/trough detection with y-axis value projection', 
                fontsize=11, transform=ax.transAxes)
        y_pos -= section_spacing
        
        # Section 6: Quality Thresholds Summary
        ax.text(0.05, y_pos, '6. QUALITY ASSESSMENT THRESHOLDS', 
                fontsize=14, weight='bold', transform=ax.transAxes, color='maroon')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Saturated: Any point < {low_thresh}V or > {high_thresh}V', 
                fontsize=11, transform=ax.transAxes, color='red')
        y_pos -= line_height
        ax.text(0.1, y_pos, f'• Low Amplitude: Average amplitude < {low_amplitude_thresh}mV (excludes REF)', 
                fontsize=11, transform=ax.transAxes, color='red')
        y_pos -= line_height
        ax.text(0.1, y_pos, '• Normal: Channels meeting all quality criteria', 
                fontsize=11, transform=ax.transAxes, color='green')
        y_pos -= section_spacing
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 3: EEG Performance Overview
        print("Generating performance overview table...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('EEG Performance Overview', fontsize=16, weight='bold')
        
        # Create a single axis for the table
        ax = plt.subplot(1, 1, 1)
        ax.axis('off')
        
        # Calculate all performance metrics
        
        # 1. Average Amplitude Analysis (recalculate to get individual channel values)
        ac_pk_pk_values = {}
        low_ac_channels = []
        for ch in channel_names:
            if ch in df.columns:
                try:
                    ac_pk_pk, _, _ = calculate_ac_pk_to_pk(df[ch].values, sampling_rate=sampling_rate)
                    ac_pk_pk_mV = ac_pk_pk * 1000  # Convert to mV
                    ac_pk_pk_values[ch] = ac_pk_pk_mV
                    # Exempt reference channels (containing "(REF)") from AC amplitude threshold
                    if ac_pk_pk_mV < low_amplitude_thresh and "(REF)" not in ch:  # Use configured threshold, exempt REF channels
                        low_ac_channels.append(ch)
                except:
                    ac_pk_pk_values[ch] = 0.0
                    # Only add to low_ac_channels if not a reference channel
                    if "(REF)" not in ch:
                        low_ac_channels.append(ch)
        
        # 2. DC Drift Analysis (recalculate to get individual values)
        dc_drift_values = {}
        for ch in channel_names:
            if ch in df.columns:
                try:
                    _, drift_range, _, _ = calculate_dc_drift(df[ch].values, sampling_rate=sampling_rate)
                    dc_drift_values[ch] = drift_range * 1000  # Convert to mV
                except:
                    dc_drift_values[ch] = 0.0
        
        # 3. Problematic Channels Analysis
        saturated_channels = set(below_saturated + above_saturated)
        low_ac_channels_set = set(low_ac_channels)
        problematic_channels = saturated_channels.union(low_ac_channels_set)
        
        # 4. Overall Saturation Calculation
        total_saturation_time = 0
        total_channels = len(channel_names)
        for ch in channel_names:
            if ch in saturation_details:
                total_saturation_time += saturation_details[ch]['total_sat_pct']
        overall_saturation_pct = total_saturation_time / total_channels if total_channels > 0 else 0
        
        # Create table content
        y_pos = 0.95
        line_height = 0.025
        section_spacing = 0.04
        
        # Title
        ax.text(0.5, y_pos, 'EEG Data Quality Performance Summary', 
                fontsize=14, weight='bold', ha='center', transform=ax.transAxes)
        y_pos -= section_spacing
        
        # Section 1: Problematic Channels
        ax.text(0.05, y_pos, '1. PROBLEMATIC CHANNELS ANALYSIS', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='red')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Total Problematic Count: {len(problematic_channels)}/{total_channels} ({len(problematic_channels)/total_channels*100:.1f}%)', 
                fontsize=10, weight='bold', transform=ax.transAxes)
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Saturated Channels: {len(saturated_channels)} channels', 
                fontsize=10, transform=ax.transAxes)
        if saturated_channels:
            sat_list = ', '.join(list(saturated_channels)[:8])  # Limit to first 8
            if len(saturated_channels) > 8:
                sat_list += f' (+{len(saturated_channels)-8} more)'
            ax.text(0.15, y_pos-line_height, sat_list, fontsize=9, transform=ax.transAxes, style='italic')
            y_pos -= line_height
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Low Amplitude (<0.5mV): {len(low_ac_channels_set)} channels (excludes REF channels)', 
                fontsize=10, transform=ax.transAxes)
        if low_ac_channels_set:
            low_ac_list = ', '.join(list(low_ac_channels_set)[:8])  # Limit to first 8
            if len(low_ac_channels_set) > 8:
                low_ac_list += f' (+{len(low_ac_channels_set)-8} more)'
            ax.text(0.15, y_pos-line_height, low_ac_list, fontsize=9, transform=ax.transAxes, style='italic')
            y_pos -= line_height
        y_pos -= section_spacing
        
        # Section 2: DC Drift Statistics
        dc_values = list(dc_drift_values.values())
        ax.text(0.05, y_pos, '2. DC DRIFT STATISTICS', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='blue')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Mean DC Drift: {np.mean(dc_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'Median DC Drift: {np.median(dc_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'DC Drift Range: {np.min(dc_values):.2f} - {np.max(dc_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= section_spacing
        
        # Section 3: Average Amplitude Statistics
        ac_values = list(ac_pk_pk_values.values())
        ax.text(0.05, y_pos, '3. AVERAGE AMPLITUDE STATISTICS', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='green')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Mean Avg Amplitude: {np.mean(ac_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'Median Avg Amplitude: {np.median(ac_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'Avg Amplitude Range: {np.min(ac_values):.2f} - {np.max(ac_values):.2f} mV', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= section_spacing
        
        # Section 4: Alpha Band SNR Statistics
        # Calculate alpha band SNR values for all channels
        alpha_snr_values_table = {}
        alpha_freq_values_table = {}
        for ch in channel_names:
            if ch in df.columns:
                try:
                    snr, peak_freq, _, _, _, _ = calculate_alpha_band_snr(df[ch].values, sampling_rate=sampling_rate)
                    alpha_snr_values_table[ch] = snr  # SNR ratio
                    alpha_freq_values_table[ch] = peak_freq
                except:
                    alpha_snr_values_table[ch] = 0.0
                    alpha_freq_values_table[ch] = 0.0
        
        alpha_snr_list = list(alpha_snr_values_table.values())
        alpha_freq_list = [f for f in alpha_freq_values_table.values() if f > 0]  # Exclude zeros
        
        ax.text(0.05, y_pos, '4. ALPHA BAND SNR STATISTICS (8-12 Hz vs 80-100 Hz)', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='purple')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Mean Alpha SNR: {np.mean(alpha_snr_list):.1f}', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'Median Alpha SNR: {np.median(alpha_snr_list):.1f}', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'Alpha SNR Range: {np.min(alpha_snr_list):.1f} - {np.max(alpha_snr_list):.1f}', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        if alpha_freq_list:
            ax.text(0.1, y_pos, f'Mean Alpha Peak Frequency: {np.mean(alpha_freq_list):.1f} Hz', 
                    fontsize=10, transform=ax.transAxes)
            y_pos -= line_height
        y_pos -= section_spacing
        
        # Section 5: Saturation Details
        ax.text(0.05, y_pos, '5. SATURATION ANALYSIS', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='red')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Saturated Channels: {num_sat}/{total_channels} ({num_sat/total_channels*100:.1f}%)', 
                fontsize=10, weight='bold', transform=ax.transAxes)
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'• Above {high_thresh}V: {len(above_saturated)} channels', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.1, y_pos, f'• Below {low_thresh}V: {len(below_saturated)} channels', 
                fontsize=10, transform=ax.transAxes)
        y_pos -= line_height
        
        # Individual saturation percentages
        if num_sat > 0:
            ax.text(0.1, y_pos, 'Individual Saturation Levels:', 
                    fontsize=10, weight='bold', transform=ax.transAxes)
            y_pos -= line_height
            
            # Sort by saturation percentage
            sorted_sat = sorted([(ch, details) for ch, details in saturation_details.items() 
                               if details['is_saturated']], 
                              key=lambda x: x[1]['total_sat_pct'], reverse=True)
            
            for ch, details in sorted_sat[:10]:  # Show top 10 most saturated
                sat_type = "Above" if details['above_pct'] > details['below_pct'] else "Below"
                ax.text(0.15, y_pos, f'{ch}: {details["total_sat_pct"]:.1f}% ({sat_type})', 
                       fontsize=9, transform=ax.transAxes)
                y_pos -= line_height * 0.8
            
            if len(sorted_sat) > 10:
                ax.text(0.15, y_pos, f'... and {len(sorted_sat)-10} more', 
                       fontsize=9, style='italic', transform=ax.transAxes)
                y_pos -= line_height
        
        y_pos -= section_spacing
        
        # Section 6: Overall System Performance
        ax.text(0.05, y_pos, '6. OVERALL SYSTEM PERFORMANCE', 
                fontsize=12, weight='bold', transform=ax.transAxes, color='purple')
        y_pos -= line_height
        
        ax.text(0.1, y_pos, f'Overall Saturation Level: {overall_saturation_pct:.2f}%', 
                fontsize=10, weight='bold', transform=ax.transAxes)
        y_pos -= line_height
        ax.text(0.15, y_pos, '(percentage of time channels spent in saturation across all saturated and unsaturated channels)', 
                fontsize=8, style='italic', transform=ax.transAxes, color='gray')
        y_pos -= line_height
        
        # Quality assessment
        quality_score = 100 - len(problematic_channels)/total_channels*100
        quality_color = 'green' if quality_score >= 80 else 'orange' if quality_score >= 60 else 'red'
        ax.text(0.1, y_pos, f'Data Quality Score: {quality_score:.1f}% ({total_channels-len(problematic_channels)}/{total_channels} good channels)', 
                fontsize=10, weight='bold', transform=ax.transAxes, color=quality_color)
        y_pos -= section_spacing * 1.5  # Extra spacing before summary
        
        # Add summary box (positioned dynamically based on content above)
        summary_text = f"""SUMMARY:
• {len(problematic_channels)} of {total_channels} channels need attention
• Overall saturation: {overall_saturation_pct:.2f}%
• Quality score: {quality_score:.1f}%"""
        
        # Ensure summary box is positioned with enough space and not too low
        summary_y_pos = min(y_pos - 0.05, 0.2)  # At least 0.05 below content, but not below 0.2
        ax.text(0.5, summary_y_pos, summary_text, transform=ax.transAxes, 
                ha='center', va='center', fontsize=11, weight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 4: All channels overview (time domain)
        print("Generating all channels time domain overview...")
        fig, ax = plt.subplots(figsize=(8.5, 11))
        fig.suptitle('All Channels - Time Domain Overview', fontsize=16, weight='bold')
        
        time = np.arange(len(df)) / 1000.0  # Convert to seconds
        colors = plt.cm.tab20(np.linspace(0, 1, len(channel_names)))
        
        for i, channel in enumerate(channel_names):
            if channel in df.columns:
                # Offset each channel for visibility
                offset = i * 0.5  # Adjust spacing as needed
                ax.plot(time, df[channel] + offset, 
                       color=colors[i], linewidth=0.5, 
                       label=f'{channel}' + (' (SAT)' if channel in below_saturated + above_saturated else ''))
        
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Amplitude (V) + Offset')
        ax.set_title('All channels with vertical offset for visibility')
        ax.grid(True, alpha=0.3)
        
        # Add legend (may be crowded but informative)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 5: All channels overview (FFT)
        print("Generating all channels FFT overview...")
        fig, ax = plt.subplots(figsize=(8.5, 11))
        fig.suptitle('All Channels - Frequency Domain Overview', fontsize=16, weight='bold')
        
        for i, channel in enumerate(channel_names):
            if channel in df.columns:
                data = df[channel].values
                freqs, psd = welch(data, fs=1000.0, nperseg=2048)
                
                # Plot only up to 100 Hz
                mask = freqs <= 100
                ax.semilogy(freqs[mask], psd[mask], 
                           color=colors[i], linewidth=1, 
                           label=f'{channel}' + (' (SAT)' if channel in below_saturated + above_saturated else ''),
                           alpha=0.7)
        
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Power Spectral Density (V²/Hz)')
        ax.set_title('All channels frequency spectra')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        
        # Add legend
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 6: Average Amplitude Analysis
        print("Generating average amplitude analysis...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Channel Average Amplitude Analysis', fontsize=16, weight='bold')
        
        # Calculate average amplitude values for all channels
        ac_pk_pk_values = {}
        print("  Calculating average amplitude for all channels...")
        for ch in channel_names:
            if ch in df.columns:
                try:
                    ac_pk_pk, _, _ = calculate_ac_pk_to_pk(df[ch].values, sampling_rate=sampling_rate)
                    ac_pk_pk_values[ch] = ac_pk_pk * 1000  # Convert to mV
                except Exception as e:
                    print(f"    Warning: Could not calculate average amplitude for {ch}: {e}")
                    ac_pk_pk_values[ch] = 0.0
        
        # Sort channels by average amplitude values (highest to lowest)
        sorted_channels = sorted(ac_pk_pk_values.items(), key=lambda x: x[1], reverse=True)
        
        # Create bar plot
        ax = plt.subplot(1, 1, 1)
        channels_sorted = [item[0] for item in sorted_channels]
        values_sorted = [item[1] for item in sorted_channels]
        
        # Color gradient from highest (red) to lowest (blue)
        colors = plt.cm.RdYlBu_r(np.linspace(0, 1, len(channels_sorted)))
        
        bars = ax.bar(range(len(channels_sorted)), values_sorted, color=colors, alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('EEG Channels (Ranked by Average Amplitude)')
        ax.set_ylabel('Average Amplitude (mV)')
        ax.set_title('All Channels Ranked by Average Amplitude (Highest to Lowest)')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-tick labels to channel names with rotation
        ax.set_xticks(range(len(channels_sorted)))
        ax.set_xticklabels(channels_sorted, rotation=45, ha='right', fontsize=9)
        
        # Add value labels on top of bars (for top 10 channels only to avoid crowding)
        for i, (bar, value) in enumerate(zip(bars[:10], values_sorted[:10])):
            height = bar.get_height()
            ax.annotate(f'{value:.1f}mV',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=7, rotation=0)
        
        # Add statistics text box (positioned at top right since bars go high to low)
        mean_ac = np.mean(values_sorted)
        median_ac = np.median(values_sorted)
        std_ac = np.std(values_sorted)
        
        stats_text = f"""Statistics:
Mean: {mean_ac:.1f} mV
Median: {median_ac:.1f} mV
Std Dev: {std_ac:.1f} mV
Range: {values_sorted[0]:.1f} - {values_sorted[-1]:.1f} mV"""
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8), 
                fontsize=10)
        
        # Add ranking indicators
        if len(sorted_channels) >= 3:
            # Highlight top 3 channels
            for i in range(min(3, len(bars))):
                bars[i].set_edgecolor('gold' if i == 0 else 'silver' if i == 1 else 'orange')
                bars[i].set_linewidth(2)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 5: DC Drift Analysis
        print("Generating DC drift analysis...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Channel DC Drift Analysis', fontsize=16, weight='bold')
        
        # Calculate DC drift values for all channels
        dc_drift_values = {}
        print("  Calculating DC drift for all channels...")
        for ch in channel_names:
            if ch in df.columns:
                try:
                    _, drift_range, _, _ = calculate_dc_drift(df[ch].values, sampling_rate=sampling_rate)
                    dc_drift_values[ch] = drift_range * 1000  # Convert to mV
                except Exception as e:
                    print(f"    Warning: Could not calculate DC drift for {ch}: {e}")
                    dc_drift_values[ch] = 0.0
        
        # Sort channels by DC drift values (highest to lowest)
        sorted_drift_channels = sorted(dc_drift_values.items(), key=lambda x: x[1], reverse=True)
        
        # Create bar plot
        ax = plt.subplot(1, 1, 1)
        drift_channels_sorted = [item[0] for item in sorted_drift_channels]
        drift_values_sorted = [item[1] for item in sorted_drift_channels]
        
        # Color gradient from highest (red) to lowest (green)
        colors = plt.cm.RdYlGn_r(np.linspace(0, 1, len(drift_channels_sorted)))
        
        bars = ax.bar(range(len(drift_channels_sorted)), drift_values_sorted, color=colors, alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('EEG Channels (Ranked by DC Drift Range)')
        ax.set_ylabel('DC Drift Range (mV)')
        ax.set_title('All Channels Ranked by DC Drift Range (Highest to Lowest)')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-tick labels to channel names with rotation
        ax.set_xticks(range(len(drift_channels_sorted)))
        ax.set_xticklabels(drift_channels_sorted, rotation=45, ha='right', fontsize=9)
        
        # Add value labels on top of bars (for top 10 channels only to avoid crowding)
        for i, (bar, value) in enumerate(zip(bars[:10], drift_values_sorted[:10])):
            height = bar.get_height()
            ax.annotate(f'{value:.1f}mV',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=7, rotation=0)
        
        # Add statistics text box (positioned at top right since bars go high to low)
        mean_drift = np.mean(drift_values_sorted)
        median_drift = np.median(drift_values_sorted)
        std_drift = np.std(drift_values_sorted)
        
        drift_stats_text = f"""Statistics:
Mean: {mean_drift:.1f} mV
Median: {median_drift:.1f} mV
Std Dev: {std_drift:.1f} mV
Range: {drift_values_sorted[0]:.1f} - {drift_values_sorted[-1]:.1f} mV"""
        
        ax.text(0.98, 0.98, drift_stats_text, transform=ax.transAxes, 
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8), 
                fontsize=10)
        
        # Add ranking indicators
        if len(sorted_drift_channels) >= 3:
            # Highlight top 3 channels with highest drift
            for i in range(min(3, len(bars))):
                bars[i].set_edgecolor('gold' if i == 0 else 'silver' if i == 1 else 'orange')
                bars[i].set_linewidth(2)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 6: Alpha Band SNR Analysis  
        print("Generating alpha band SNR analysis...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Channel Alpha Band SNR Analysis (8-12 Hz vs 80-100 Hz)', fontsize=16, weight='bold')
        
        # Calculate alpha band SNR values for all channels
        alpha_snr_values = {}
        alpha_freq_values = {}
        alpha_amplitude_values = {}
        print("  Calculating alpha band SNR for all channels...")
        for ch in channel_names:
            if ch in df.columns:
                try:
                    snr, peak_freq, peak_amplitude, noise_floor, freqs, psd = calculate_alpha_band_snr(df[ch].values, sampling_rate=sampling_rate)
                    alpha_snr_values[ch] = snr  # SNR ratio (dimensionless)
                    alpha_freq_values[ch] = peak_freq
                    alpha_amplitude_values[ch] = peak_amplitude  # Keep as V²/Hz (PSD units)
                except Exception as e:
                    print(f"    Warning: Could not calculate alpha band SNR for {ch}: {e}")
                    alpha_snr_values[ch] = 0.0
                    alpha_freq_values[ch] = 0.0
                    alpha_amplitude_values[ch] = 0.0
        
        # Sort channels by alpha SNR (highest to lowest)
        sorted_alpha_channels = sorted(alpha_snr_values.items(), key=lambda x: x[1], reverse=True)
        
        # Create bar plot
        ax = plt.subplot(1, 1, 1)
        alpha_channels_sorted = [item[0] for item in sorted_alpha_channels]
        alpha_values_sorted = [item[1] for item in sorted_alpha_channels]
        
        # Color gradient from highest (purple) to lowest (yellow)
        colors = plt.cm.plasma(np.linspace(0, 1, len(alpha_channels_sorted)))
        
        bars = ax.bar(range(len(alpha_channels_sorted)), alpha_values_sorted, color=colors, alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('EEG Channels (Ranked by Alpha Band SNR)')
        ax.set_ylabel('Alpha SNR (signal/noise ratio)')
        ax.set_title('All Channels Ranked by Alpha Band SNR (Highest to Lowest)')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-tick labels to channel names with rotation
        ax.set_xticks(range(len(alpha_channels_sorted)))
        ax.set_xticklabels(alpha_channels_sorted, rotation=45, ha='right', fontsize=9)
        
        # Add value labels on top of bars (for top 10 channels only to avoid crowding)
        for i, (bar, value) in enumerate(zip(bars[:10], alpha_values_sorted[:10])):
            height = bar.get_height()
            # Also show the frequency of the peak
            peak_freq = alpha_freq_values[alpha_channels_sorted[i]]
            ax.annotate(f'{value:.1f}\n{peak_freq:.1f}Hz',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=6, rotation=0)
        
        # Add statistics text box (positioned at top right since bars go high to low)
        mean_alpha = np.mean(alpha_values_sorted)
        median_alpha = np.median(alpha_values_sorted)
        std_alpha = np.std(alpha_values_sorted)
        
        # Also calculate frequency statistics
        all_peak_freqs = [alpha_freq_values[ch] for ch in alpha_channels_sorted]
        mean_freq = np.mean([f for f in all_peak_freqs if f > 0])  # Exclude zeros
        
        alpha_stats_text = f"""Alpha Band SNR Statistics:
SNR Mean: {mean_alpha:.1f}
SNR Median: {median_alpha:.1f}  
SNR Std Dev: {std_alpha:.1f}
SNR Range: {alpha_values_sorted[0]:.1f} - {alpha_values_sorted[-1]:.1f}

Peak Freq Mean: {mean_freq:.1f} Hz"""
        
        ax.text(0.98, 0.98, alpha_stats_text, transform=ax.transAxes, 
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='plum', alpha=0.8), 
                fontsize=9)
        
        # Add ranking indicators
        if len(sorted_alpha_channels) >= 3:
            # Highlight top 3 channels with highest alpha SNR
            for i in range(min(3, len(bars))):
                bars[i].set_edgecolor('gold' if i == 0 else 'silver' if i == 1 else 'orange')
                bars[i].set_linewidth(2)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 7: Channel Information Table
        print("Generating channel information table...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Complete Channel Information Table', fontsize=16, weight='bold')
        
        # Create table data
        table_data = []
        headers = ['Ch#', 'Name', 'Status', 'Avg Amplitude\n(mV)', 'DC Drift\n(mV)', 'Sat Time\n(%)', 'Alpha SNR', 'Alpha Freq\n(Hz)']
        
        # Get channel mapping for proper ordering
        if use_channel_mapping:
            try:
                channel_map = load_channel_map(channel_mapping_file)
                # Sort by channel number
                sorted_channel_items = sorted(channel_map.items(), key=lambda x: int(x[0].split()[-1]))
            except:
                sorted_channel_items = [(f"Ch{i+1}", ch) for i, ch in enumerate(channel_names)]
        else:
            sorted_channel_items = [(f"Ch{i+1}", ch) for i, ch in enumerate(channel_names)]
        
        for csv_name, channel in sorted_channel_items:
            if channel not in df.columns:
                continue
                
            # Get channel data
            data = df[channel].values
            
            # Calculate all metrics
            try:
                # Average Amplitude
                ac_pk_pk, _, _ = calculate_ac_pk_to_pk(data, sampling_rate=sampling_rate)
                ac_pk_pk_mV = ac_pk_pk * 1000
            except:
                ac_pk_pk_mV = 0.0
            
            try:
                # DC Drift
                _, drift_range, _, _ = calculate_dc_drift(data, sampling_rate=sampling_rate)
                drift_range_mV = drift_range * 1000
            except:
                drift_range_mV = 0.0
            
            try:
                # Alpha band SNR
                alpha_snr, alpha_freq, _, _, _, _ = calculate_alpha_band_snr(data, sampling_rate=sampling_rate)
            except:
                alpha_snr = 0.0
                alpha_freq = 0.0
            
            # Saturation info
            sat_time_pct = saturation_details.get(channel, {}).get('total_sat_pct', 0.0)
            
            # Determine status
            status_parts = []
            if channel in below_saturated or channel in above_saturated:
                status_parts.append("SAT")
            # Exempt reference channels from low amplitude status
            if ac_pk_pk_mV < low_amplitude_thresh and "(REF)" not in channel:
                status_parts.append("LOW-AMP")
            
            status = ", ".join(status_parts) if status_parts else "NORMAL"
            
            # Format row data
            row = [
                csv_name.replace("Channel ", "Ch"),  # Channel number
                channel,  # Channel name
                status,   # Status
                f"{ac_pk_pk_mV:.1f}",  # Avg Amplitude
                f"{drift_range_mV:.1f}",  # DC Drift
                f"{sat_time_pct:.1f}" if sat_time_pct > 0 else "0.0",  # Saturation time
                f"{alpha_snr:.1f}",  # Alpha SNR
                f"{alpha_freq:.1f}" if alpha_freq > 0 else "N/A"  # Alpha frequency
            ]
            table_data.append(row)
        
        # Create the table
        ax = plt.subplot(1, 1, 1)
        ax.axis('off')
        
        # Create table with matplotlib
        table = ax.table(cellText=table_data, colLabels=headers, 
                        cellLoc='center', loc='center',
                        bbox=[0.02, 0.1, 0.96, 0.8])
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.2)
        
        # Color code the status column (column index 2)
        for i, row in enumerate(table_data):
            status = row[2]
            if "SAT" in status or "LOW-AMP" in status:
                # Color problematic channels red
                table[(i+1, 2)].set_facecolor('#ffcccc')  # Light red
                table[(i+1, 0)].set_facecolor('#ffeeee')  # Very light red for channel number
                table[(i+1, 1)].set_facecolor('#ffeeee')  # Very light red for channel name
            else:
                # Color normal channels light green
                table[(i+1, 2)].set_facecolor('#ccffcc')  # Light green
        
        # Style headers
        for j in range(len(headers)):
            table[(0, j)].set_facecolor('#4472C4')  # Blue header
            table[(0, j)].set_text_props(weight='bold', color='white')
        
        # Add summary information
        ax.text(0.5, 0.05, f'Total Channels: {len(table_data)} | Normal: {len([r for r in table_data if r[2] == "NORMAL"])} | Problematic: {len([r for r in table_data if r[2] != "NORMAL"])}', 
                ha='center', transform=ax.transAxes, fontsize=10, weight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 8: Saturation Analysis
        print("Generating saturation analysis...")
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('Channel Saturation Analysis', fontsize=16, weight='bold')
        
        # Create text summary
        ax_text = plt.subplot(2, 1, 1)
        ax_text.axis('off')
        
        y_pos = 0.95
        line_height = 0.08
        
        ax_text.text(0.05, y_pos, f'Saturation Summary:', fontsize=14, weight='bold', transform=ax_text.transAxes)
        y_pos -= line_height
        
        ax_text.text(0.05, y_pos, f'• Total saturated channels: {num_sat}/{len(channel_names)} ({num_sat/len(channel_names)*100:.1f}%)', 
                     fontsize=12, transform=ax_text.transAxes)
        y_pos -= line_height
        
        ax_text.text(0.05, y_pos, f'• Channels below {low_thresh}V: {len(below_saturated)}', 
                     fontsize=12, transform=ax_text.transAxes)
        y_pos -= line_height
        
        ax_text.text(0.05, y_pos, f'• Channels above {high_thresh}V: {len(above_saturated)}', 
                     fontsize=12, transform=ax_text.transAxes)
        y_pos -= line_height * 1.5
        
        if num_sat > 0:
            ax_text.text(0.05, y_pos, 'Saturated Channels Details:', fontsize=12, weight='bold', transform=ax_text.transAxes)
            y_pos -= line_height
            
            # Sort by saturation percentage
            sorted_sat = sorted(saturation_details.items(), 
                              key=lambda x: x[1]['total_sat_pct'], reverse=True)
            
            count = 0
            for ch, details in sorted_sat:
                if details['is_saturated'] and count < 15:  # Limit to prevent overcrowding
                    sat_type = "Below" if details['below_pct'] > details['above_pct'] else "Above"
                    sat_pct = max(details['below_pct'], details['above_pct'])
                    ax_text.text(0.1, y_pos, f'{ch}: {sat_pct:.1f}% ({sat_type})', 
                               fontsize=10, transform=ax_text.transAxes)
                    y_pos -= line_height * 0.8
                    count += 1
            
            if num_sat > 15:
                ax_text.text(0.1, y_pos, f'... and {num_sat - 15} more', 
                           fontsize=10, style='italic', transform=ax_text.transAxes)
        else:
            ax_text.text(0.05, y_pos, 'No saturated channels detected ✓', 
                         fontsize=12, color='green', weight='bold', transform=ax_text.transAxes)
        
        # Create bar chart of saturation percentages (only for saturated channels)
        if saturation_details and num_sat > 0:
            ax_bar = plt.subplot(2, 1, 2)
            
            # Get only saturated channels and their saturation percentages
            saturated_channels = [ch for ch, details in saturation_details.items() 
                                if details['is_saturated']]
            sat_percentages = [saturation_details[ch]['total_sat_pct'] for ch in saturated_channels]
            
            # Color bars: red for above threshold, blue for below threshold
            colors_bar = []
            for ch in saturated_channels:
                details = saturation_details[ch]
                if details['above_pct'] > details['below_pct']:
                    colors_bar.append('red')  # Above threshold saturation
                else:
                    colors_bar.append('blue')  # Below threshold saturation
            
            bars = ax_bar.bar(range(len(saturated_channels)), sat_percentages, color=colors_bar, alpha=0.7)
            ax_bar.set_xlabel('Saturated Channels')
            ax_bar.set_ylabel('Max Saturation %')
            ax_bar.set_title(f'Saturation Percentages for {len(saturated_channels)} Saturated Channels')
            ax_bar.grid(True, alpha=0.3, axis='y')
            
            # Add threshold line
            ax_bar.axhline(y=percent*100, color='orange', linestyle='--', 
                          label=f'Threshold ({percent*100}%)')
            ax_bar.legend()
            
            # Set x-tick labels to channel names
            ax_bar.set_xticks(range(len(saturated_channels)))
            ax_bar.set_xticklabels(saturated_channels, rotation=45, ha='right')
        elif saturation_details:
            # If no saturated channels, show a message
            ax_bar = plt.subplot(2, 1, 2)
            ax_bar.text(0.5, 0.5, 'No saturated channels to display ✓', 
                       ha='center', va='center', fontsize=14, color='green', 
                       weight='bold', transform=ax_bar.transAxes)
            ax_bar.set_title('Channel Saturation Analysis')
            ax_bar.axis('off')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Pages 9-12: Dashboard Overview (4x4 panel layouts)
        
        # Get channel mapping for proper channel numbering and problematic channel identification
        channel_map = {}
        reverse_channel_map = {}
        if use_channel_mapping:
            try:
                channel_map = load_channel_map(channel_mapping_file)
                reverse_channel_map = {electrode: csv_name for csv_name, electrode in channel_map.items()}
            except:
                pass
        
        # Identify problematic channels for highlighting
        problematic_channel_names = set()
        for channel in channel_names:
            if channel in below_saturated or channel in above_saturated:
                problematic_channel_names.add(channel)
            # Check low amplitude (< 5mV) - exempt reference channels
            if channel in df.columns:
                try:
                    ac_pk_pk, _, _ = calculate_ac_pk_to_pk(df[channel].values, sampling_rate=sampling_rate)
                    if ac_pk_pk * 1000 < low_amplitude_thresh and "(REF)" not in channel:
                        problematic_channel_names.add(channel)
                except:
                    pass
        
        # Create ordered list of channels by channel number (1-32)
        ordered_channels = []
        for i in range(1, 33):  # Channels 1-32
            csv_name = f"Channel {i}"
            if csv_name in channel_map:
                electrode_name = channel_map[csv_name]
                if electrode_name in df.columns:
                    ordered_channels.append((i, csv_name, electrode_name))
        
        # Page 10: Dashboard Overview - Time Domain Channels 1-16
        print("Generating dashboard overview - Time domain channels 1-16...")
        fig = plt.figure(figsize=(16, 12))  # Landscape orientation
        fig.suptitle('Dashboard Overview: Time Domain Channels 1-16', fontsize=20, weight='bold')
        
        for plot_idx in range(16):
            if plot_idx < len(ordered_channels):
                ch_num, csv_name, electrode_name = ordered_channels[plot_idx]
                
                # Create subplot (4x4 grid)
                ax = plt.subplot(4, 4, plot_idx + 1)
                
                # Get channel data
                data = df[electrode_name].values
                time = np.arange(len(data)) / 1000.0  # Convert to seconds
                
                # Plot raw time domain data (no annotations)
                ax.plot(time, data, 'b-', linewidth=0.5, alpha=0.8)
                
                # Format the title based on whether it's problematic
                is_problematic = electrode_name in problematic_channel_names
                title_color = 'red' if is_problematic else 'black'
                problem_indicator = " (PROBLEMATIC)" if is_problematic else ""
                
                ax.set_title(f'Ch{ch_num}: {electrode_name}{problem_indicator}', 
                           fontsize=10, weight='bold', color=title_color)
                ax.set_xlabel('Time (s)', fontsize=8)
                ax.set_ylabel('Amplitude (V)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                
                # Scale y-axis to signal range (like individual plots)
                data_min, data_max = np.min(data), np.max(data)
                data_range = data_max - data_min
                margin = data_range * 0.1  # 10% margin
                ax.set_ylim(data_min - margin, data_max + margin)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 11: Dashboard Overview - Time Domain Channels 17-32
        print("Generating dashboard overview - Time domain channels 17-32...")
        fig = plt.figure(figsize=(16, 12))  # Landscape orientation
        fig.suptitle('Dashboard Overview: Time Domain Channels 17-32', fontsize=20, weight='bold')
        
        for plot_idx in range(16):
            ch_idx = plot_idx + 16  # Channels 17-32
            if ch_idx < len(ordered_channels):
                ch_num, csv_name, electrode_name = ordered_channels[ch_idx]
                
                # Create subplot (4x4 grid)
                ax = plt.subplot(4, 4, plot_idx + 1)
                
                # Get channel data
                data = df[electrode_name].values
                time = np.arange(len(data)) / 1000.0  # Convert to seconds
                
                # Plot raw time domain data (no annotations)
                ax.plot(time, data, 'b-', linewidth=0.5, alpha=0.8)
                
                # Format the title based on whether it's problematic
                is_problematic = electrode_name in problematic_channel_names
                title_color = 'red' if is_problematic else 'black'
                problem_indicator = " (PROBLEMATIC)" if is_problematic else ""
                
                ax.set_title(f'Ch{ch_num}: {electrode_name}{problem_indicator}', 
                           fontsize=10, weight='bold', color=title_color)
                ax.set_xlabel('Time (s)', fontsize=8)
                ax.set_ylabel('Amplitude (V)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                
                # Scale y-axis to signal range (like individual plots)
                data_min, data_max = np.min(data), np.max(data)
                data_range = data_max - data_min
                margin = data_range * 0.1  # 10% margin
                ax.set_ylim(data_min - margin, data_max + margin)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 12: Dashboard Overview - FFT Channels 1-16
        print("Generating dashboard overview - FFT channels 1-16...")
        fig = plt.figure(figsize=(16, 12))  # Landscape orientation
        fig.suptitle('Dashboard Overview: FFT Channels 1-16', fontsize=20, weight='bold')
        
        for plot_idx in range(16):
            if plot_idx < len(ordered_channels):
                ch_num, csv_name, electrode_name = ordered_channels[plot_idx]
                
                # Create subplot (4x4 grid)
                ax = plt.subplot(4, 4, plot_idx + 1)
                
                # Get channel data
                data = df[electrode_name].values
                
                # Compute power spectral density using Welch's method
                freqs, psd = welch(data, fs=1000.0, nperseg=2048)
                
                # Plot only up to 100 Hz for EEG relevance
                mask = freqs <= 100
                freqs = freqs[mask]
                psd = psd[mask]
                
                ax.semilogy(freqs, psd, 'r-', linewidth=0.8, alpha=0.8)
                
                # Format the title based on whether it's problematic
                is_problematic = electrode_name in problematic_channel_names
                title_color = 'red' if is_problematic else 'black'
                problem_indicator = " (PROBLEMATIC)" if is_problematic else ""
                
                ax.set_title(f'Ch{ch_num}: {electrode_name}{problem_indicator}', 
                           fontsize=10, weight='bold', color=title_color)
                ax.set_xlabel('Frequency (Hz)', fontsize=8)
                ax.set_ylabel('PSD (V²/Hz)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                ax.set_xlim(0, 100)
                
                # Add alpha band highlighting
                ax.axvspan(8, 12, alpha=0.1, color='green')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Page 13: Dashboard Overview - FFT Channels 17-32
        print("Generating dashboard overview - FFT channels 17-32...")
        fig = plt.figure(figsize=(16, 12))  # Landscape orientation
        fig.suptitle('Dashboard Overview: FFT Channels 17-32', fontsize=20, weight='bold')
        
        for plot_idx in range(16):
            ch_idx = plot_idx + 16  # Channels 17-32
            if ch_idx < len(ordered_channels):
                ch_num, csv_name, electrode_name = ordered_channels[ch_idx]
                
                # Create subplot (4x4 grid)
                ax = plt.subplot(4, 4, plot_idx + 1)
                
                # Get channel data
                data = df[electrode_name].values
                
                # Compute power spectral density using Welch's method
                freqs, psd = welch(data, fs=1000.0, nperseg=2048)
                
                # Plot only up to 100 Hz for EEG relevance
                mask = freqs <= 100
                freqs = freqs[mask]
                psd = psd[mask]
                
                ax.semilogy(freqs, psd, 'r-', linewidth=0.8, alpha=0.8)
                
                # Format the title based on whether it's problematic
                is_problematic = electrode_name in problematic_channel_names
                title_color = 'red' if is_problematic else 'black'
                problem_indicator = " (PROBLEMATIC)" if is_problematic else ""
                
                ax.set_title(f'Ch{ch_num}: {electrode_name}{problem_indicator}', 
                           fontsize=10, weight='bold', color=title_color)
                ax.set_xlabel('Frequency (Hz)', fontsize=8)
                ax.set_ylabel('PSD (V²/Hz)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                ax.set_xlim(0, 100)
                
                # Add alpha band highlighting
                ax.axvspan(8, 12, alpha=0.1, color='green')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Pages 14+: Individual channel plots - organized by problematic vs normal
        
        # Create reverse mapping from electrode names to channel numbers
        reverse_channel_map = {}
        if use_channel_mapping:
            try:
                channel_map = load_channel_map(channel_mapping_file)
                reverse_channel_map = {electrode: csv_name for csv_name, electrode in channel_map.items()}
            except:
                pass
        
        # Define a custom sorting function for alphanumeric channel names
        def natural_sort_key(channel_name):
            """Sort channel names naturally (e.g., AF3, AF4, F3, F4, F7, F8, etc.)"""
            import re
            # Split into alphabetical and numerical parts
            parts = re.findall(r'[A-Za-z]+|\d+', channel_name)
            # Convert numbers to integers for proper sorting, keep letters as strings
            return [int(part) if part.isdigit() else part for part in parts]
        
        # Separate and sort channels
        problematic_channels_list = []
        normal_channels_list = []
        
        # Get AC values for low amplitude detection
        ac_pk_pk_values_sorted = {}
        for ch in channel_names:
            if ch in df.columns:
                try:
                    ac_pk_pk, _, _ = calculate_ac_pk_to_pk(df[ch].values, sampling_rate=sampling_rate)
                    ac_pk_pk_values_sorted[ch] = ac_pk_pk * 1000  # Convert to mV
                except:
                    ac_pk_pk_values_sorted[ch] = 0.0
        
        # Classify channels
        for channel in channel_names:
            if channel not in df.columns:
                continue
                
            is_problematic = False
            
            # Check if saturated
            if channel in below_saturated or channel in above_saturated:
                is_problematic = True
            
            # Check if low amplitude (< threshold mV) - exempt reference channels
            if channel in ac_pk_pk_values_sorted and ac_pk_pk_values_sorted[channel] < low_amplitude_thresh and "(REF)" not in channel:
                is_problematic = True
            
            if is_problematic:
                problematic_channels_list.append(channel)
            else:
                normal_channels_list.append(channel)
        
        # Sort both lists alphabetically/numerically
        problematic_channels_list.sort(key=natural_sort_key)
        normal_channels_list.sort(key=natural_sort_key)
        
        print(f"Identified {len(problematic_channels_list)} problematic channels: {problematic_channels_list}")
        print(f"Identified {len(normal_channels_list)} normal channels")
        
        # Page: Problematic Channels Section Divider
        if problematic_channels_list:
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.text(0.5, 0.7, 'PROBLEMATIC CHANNELS', fontsize=28, ha='center', weight='bold', color='red')
            ax.text(0.5, 0.55, f'{len(problematic_channels_list)} channels requiring attention', 
                    fontsize=16, ha='center', style='italic')
            
            # List the problematic channels with their issues
            y_pos = 0.45
            ax.text(0.5, y_pos, 'Issues Identified:', fontsize=14, ha='center', weight='bold')
            y_pos -= 0.05
            
            for i, channel in enumerate(problematic_channels_list):
                issues = []
                if channel in below_saturated or channel in above_saturated:
                    sat_pct = saturation_details.get(channel, {}).get('total_sat_pct', 0)
                    issues.append(f"Saturated ({sat_pct:.1f}%)")
                if channel in ac_pk_pk_values_sorted and ac_pk_pk_values_sorted[channel] < low_amplitude_thresh:
                    issues.append(f"Low Amplitude ({ac_pk_pk_values_sorted[channel]:.2f}mV)")
                
                issue_text = f"{channel}: {', '.join(issues)}"
                ax.text(0.5, y_pos, issue_text, fontsize=11, ha='center', 
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7))
                y_pos -= 0.04
                
                # Prevent text from going too low
                if y_pos < 0.1:
                    break
            
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
            # Plot problematic channels
            for i, channel in enumerate(problematic_channels_list):
                print(f"Processing problematic channel {i+1}/{len(problematic_channels_list)}: {channel}")
                
                # Create figure with 2 subplots (time domain and FFT)
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 11))
                
                # Add detailed problem indicator to title
                problems = []
                if channel in below_saturated or channel in above_saturated:
                    sat_pct = saturation_details.get(channel, {}).get('total_sat_pct', 0)
                    problems.append(f"SATURATED ({sat_pct:.1f}%)")
                if channel in ac_pk_pk_values_sorted and ac_pk_pk_values_sorted[channel] < low_amplitude_thresh:
                    problems.append(f"LOW AMP ({ac_pk_pk_values_sorted[channel]:.2f}mV)")
                
                problem_text = f" - {', '.join(problems)}" if problems else ""
                
                # Add channel number to title if available
                channel_number = reverse_channel_map.get(channel, "")
                channel_title = f"{channel_number}: {channel}" if channel_number else channel
                
                fig.suptitle(f'PROBLEMATIC: {channel_title}{problem_text}', 
                            fontsize=14, weight='bold', color='red')
                
                # Get channel data
                data = df[channel].values
                
                # Plot time domain
                plot_time_domain(ax1, data, channel)
                
                # Add saturation threshold lines to time domain plot
                ax1.axhline(y=low_thresh, color='red', linestyle='--', alpha=0.7, label=f'Low thresh ({low_thresh}V)')
                ax1.axhline(y=high_thresh, color='red', linestyle='--', alpha=0.7, label=f'High thresh ({high_thresh}V)')
                ax1.legend()
                
                # Add detailed problem information box to time domain plot
                problem_details = []
                if channel in below_saturated:
                    below_pct = saturation_details.get(channel, {}).get('below_pct', 0)
                    problem_details.append(f"Saturated Below {low_thresh}V: {below_pct:.1f}% of time")
                if channel in above_saturated:
                    above_pct = saturation_details.get(channel, {}).get('above_pct', 0)
                    problem_details.append(f"Saturated Above {high_thresh}V: {above_pct:.1f}% of time")
                if channel in ac_pk_pk_values_sorted and ac_pk_pk_values_sorted[channel] < low_amplitude_thresh and "(REF)" not in channel:
                    ac_value = ac_pk_pk_values_sorted[channel]
                    problem_details.append(f"Low Amplitude: {ac_value:.2f}mV (< {low_amplitude_thresh}mV threshold)")
                
                if problem_details:
                    problem_info = "IDENTIFIED PROBLEMS:\n" + "\n".join([f"• {detail}" for detail in problem_details])
                    ax1.text(0.02, 0.85, problem_info, transform=ax1.transAxes, 
                            verticalalignment='top', horizontalalignment='left',
                            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.9),
                            fontsize=8, weight='bold')
                
                # Plot FFT
                plot_fft_high_accuracy(ax2, data, channel)
                
                # Add alpha band SNR information and visual annotations to FFT plot for problematic channels
                try:
                    alpha_snr, alpha_peak_freq, alpha_peak_amplitude, noise_floor, freqs, psd = calculate_alpha_band_snr(data, sampling_rate=sampling_rate)
                    alpha_info = f"Alpha Band SNR:\nSNR: {alpha_snr:.1f}\nPeak Freq: {alpha_peak_freq:.1f} Hz\nPeak Amp: {alpha_peak_amplitude:.2e} V²/Hz"
                    ax2.text(0.98, 0.98, alpha_info, transform=ax2.transAxes,
                            verticalalignment='top', horizontalalignment='right',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='plum', alpha=0.8),
                            fontsize=8)
                    
                    # Add visual annotations to FFT plot
                    # Mark alpha peak with a dot
                    ax2.plot(alpha_peak_freq, alpha_peak_amplitude, 'ro', markersize=6, label=f'Alpha Peak ({alpha_peak_freq:.1f}Hz)')
                    
                    # Draw noise floor line (80-100 Hz)
                    noise_freq_range = np.linspace(80, 100, 100)
                    noise_floor_line = np.full_like(noise_freq_range, noise_floor)
                    ax2.plot(noise_freq_range, noise_floor_line, '--', color='gray', alpha=0.7, linewidth=1, 
                            label=f'Noise Floor ({noise_floor:.2e} V²/Hz)')
                    
                    # Add legend for annotations
                    ax2.legend(loc='upper right', bbox_to_anchor=(0.95, 0.75), fontsize=8)
                except:
                    pass
                
                # Adjust layout
                plt.tight_layout()
                plt.subplots_adjust(top=0.90)
                
                # Save to PDF
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        
        # Page: Normal Channels Section Divider
        if normal_channels_list:
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.text(0.5, 0.6, 'REMAINING NORMAL CHANNELS', fontsize=24, ha='center', weight='bold', color='green')
            ax.text(0.5, 0.45, f'{len(normal_channels_list)} channels with good signal quality', 
                    fontsize=16, ha='center', style='italic')
            
            # Show the normal channels in a grid format
            ax.text(0.5, 0.35, 'Normal Channels:', fontsize=14, ha='center', weight='bold')
            
            # Display normal channels in rows
            channels_per_row = 8
            y_start = 0.3
            for i, channel in enumerate(normal_channels_list):
                row = i // channels_per_row
                col = i % channels_per_row
                x_pos = 0.1 + (col * 0.1)
                y_pos = y_start - (row * 0.03)
                
                if y_pos > 0.05:  # Only show if there's space
                    ax.text(x_pos, y_pos, channel, fontsize=10, ha='left',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='lightgreen', alpha=0.7))
            
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
            # Plot normal channels
            for i, channel in enumerate(normal_channels_list):
                print(f"Processing normal channel {i+1}/{len(normal_channels_list)}: {channel}")
                
                # Create figure with 2 subplots (time domain and FFT)
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 11))
                
                # Add channel number to title if available
                channel_number = reverse_channel_map.get(channel, "")
                channel_title = f"{channel_number}: {channel}" if channel_number else channel
                
                fig.suptitle(f'NORMAL: {channel_title}', 
                            fontsize=16, weight='bold', color='green')
                
                # Get channel data
                data = df[channel].values
                
                # Plot time domain
                plot_time_domain(ax1, data, channel)
                
                # Add saturation threshold lines to time domain plot (lighter for normal channels)
                ax1.axhline(y=low_thresh, color='gray', linestyle='--', alpha=0.3, label=f'Low thresh ({low_thresh}V)')
                ax1.axhline(y=high_thresh, color='gray', linestyle='--', alpha=0.3, label=f'High thresh ({high_thresh}V)')
                ax1.legend()
                
                # Plot FFT
                plot_fft_high_accuracy(ax2, data, channel)
                
                # Add alpha band SNR information and visual annotations to FFT plot for normal channels
                try:
                    alpha_snr, alpha_peak_freq, alpha_peak_amplitude, noise_floor, freqs, psd = calculate_alpha_band_snr(data, sampling_rate=sampling_rate)
                    alpha_info = f"Alpha Band SNR:\nSNR: {alpha_snr:.1f}\nPeak Freq: {alpha_peak_freq:.1f} Hz\nPeak Amp: {alpha_peak_amplitude:.2e} V²/Hz"
                    ax2.text(0.98, 0.98, alpha_info, transform=ax2.transAxes,
                            verticalalignment='top', horizontalalignment='right',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.8),
                            fontsize=8)
                    
                    # Add visual annotations to FFT plot
                    # Mark alpha peak with a dot
                    ax2.plot(alpha_peak_freq, alpha_peak_amplitude, 'ro', markersize=6, label=f'Alpha Peak ({alpha_peak_freq:.1f}Hz)')
                    
                    # Draw noise floor line (80-100 Hz)
                    noise_freq_range = np.linspace(80, 100, 100)
                    noise_floor_line = np.full_like(noise_freq_range, noise_floor)
                    ax2.plot(noise_freq_range, noise_floor_line, '--', color='gray', alpha=0.7, linewidth=1, 
                            label=f'Noise Floor ({noise_floor:.2e} V²/Hz)')
                    
                    # Add legend for annotations
                    ax2.legend(loc='upper right', bbox_to_anchor=(0.95, 0.75), fontsize=8)
                except:
                    pass
                
                # Adjust layout
                plt.tight_layout()
                plt.subplots_adjust(top=0.93)
                
                # Save to PDF
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

    
    print(f"Report generated successfully: {output_pdf_path}")
    
    # Move the original CSV file to the same date folder
    move_source_csv(csv_file, output_paths['output_folder'])
    
    # Updated page count: 1 cover + 1 methods + 1 performance + 7 overview pages + 4 dashboard pages + 2 section dividers + all channel pages
    section_dividers = 2 if len(channel_names) > 0 else 0
    total_pages = 1 + 1 + 1 + 7 + 4 + section_dividers + len(channel_names)
    print(f"Total pages: {total_pages}")
    print(f"  - Cover page: 1")
    print(f"  - Methods summary: 1")
    print(f"  - Performance overview: 1")
    print(f"  - Analysis pages: 7")
    print(f"  - Dashboard pages: 4")
    print(f"  - Section dividers: {section_dividers}")
    print(f"  - Individual channel pages: {len(channel_names)}")
    print(f"Files saved in output folder: {output_paths['output_folder']}")
    return output_pdf_path

def scan_for_csv_files(directory):
    """
    Scan a directory for CSV files and return a list of found files.
    
    Parameters:
        directory (str): Directory to scan
        
    Returns:
        list: List of CSV file paths
    """
    csv_files = []
    try:
        for file in os.listdir(directory):
            if file.endswith('.csv') and os.path.isfile(os.path.join(directory, file)):
                csv_files.append(os.path.join(directory, file))
    except PermissionError:
        print(f"Warning: No permission to read directory {directory}")
    except FileNotFoundError:
        print(f"Warning: Directory {directory} not found")
    
    return sorted(csv_files)


def interactive_file_selection():
    """
    Interactively select a CSV file from the current directory.
    
    Returns:
        str: Path to selected CSV file, or None if cancelled
    """
    clear_screen()
    
    current_dir = os.getcwd()
    print(f"\nScanning for CSV files in: {current_dir}")
    
    csv_files = scan_for_csv_files(current_dir)
    
    if not csv_files:
        print("No CSV files found in the current directory.")
        return None
    
    print(f"\nFound {len(csv_files)} CSV file(s):")
    print("-" * 50)
    
    for i, file_path in enumerate(csv_files, 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Get file modification time
        mod_time = os.path.getmtime(file_path)
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        
        print(f"{i:2d}. {filename:<30} ({file_size_mb:.1f} MB, {mod_time_str})")
    
    print("-" * 50)
    
    while True:
        try:
            choice = input(f"\nSelect a file (1-{len(csv_files)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            file_index = int(choice) - 1
            
            if 0 <= file_index < len(csv_files):
                selected_file = csv_files[file_index]
                filename = os.path.basename(selected_file)
                print(f"\nSelected: {filename}")
                return selected_file
            else:
                print(f"Please enter a number between 1 and {len(csv_files)}")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def main():
    """Main function to handle command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate EEG channel analysis report')
    parser.add_argument('csv_file', nargs='?', default=None, help='Path to the CSV file containing EEG data (optional - if not provided, interactive selection will be used)')
    parser.add_argument('output_pdf', nargs='?', default=None, help='Output PDF filename (optional)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Force interactive file selection even if csv_file is provided')
    
    args = parser.parse_args()
    
    # Determine which file to use
    csv_file = None
    
    if args.interactive or args.csv_file is None:
        # Use interactive selection
        csv_file = interactive_file_selection()
        if csv_file is None:
            sys.exit(0)  # User cancelled
    else:
        # Use provided file path
        csv_file = args.csv_file
    
    # Convert to absolute path and normalize path separators
    csv_file = os.path.abspath(csv_file)
    
    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    
    # Interactive channel mapping selection
    channel_mapping_file = interactive_channel_mapping_selection()
    if channel_mapping_file is None:
        print("Channel mapping selection cancelled.")
        sys.exit(0)
    
    # Check if user chose no channel mapping
    use_channel_mapping = channel_mapping_file != "none"
    if not use_channel_mapping:
        channel_mapping_file = None

    # Interactive folder selection
    selected_folder = interactive_folder_selection()
    if selected_folder is None:
        print("Folder selection cancelled.")
        sys.exit(0)

    # Interactive threshold selection
    threshold_config = interactive_threshold_selection()
    if threshold_config is None:
        print("Threshold configuration cancelled.")
        sys.exit(0)

    # Interactive filter selection
    filter_config = interactive_filter_selection()
    if filter_config is None:
        print("Filter configuration cancelled.")
        sys.exit(0)

    # Get the output filename (interactive if not provided)
    output_filename = get_output_filename(csv_file, args.output_pdf)
    
    try:
        output_pdf_path = generate_eeg_report(
            csv_file=csv_file,
            output_pdf=output_filename,
            use_channel_mapping=use_channel_mapping,
            low_thresh=threshold_config['low_thresh'],
            high_thresh=threshold_config['high_thresh'],
            low_amplitude_thresh=threshold_config['low_amplitude_thresh'],
            channel_mapping_file=channel_mapping_file,
            custom_folder=selected_folder,
            filter_config=filter_config
        )
        print(f"\nPDF report successfully generated!")
        
        # Automatically open the PDF file
        open_pdf_file(output_pdf_path)
    except Exception as e:
        print(f"Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
