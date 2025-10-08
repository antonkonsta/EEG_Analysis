#!/usr/bin/env python3
"""
Dashboard Integration for EEG Analysis

This module provides the integration layer between the dashboard UI
and the existing EEG analysis functions.
"""

import os
import sys
from typing import List, Optional, Tuple

# Import colorama for colored output
try:
    from colorama import Fore, Back, Style, init
    init()
except ImportError:
    # Fallback if colorama is not available
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = BLACK = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = BLACK = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

# Import the dashboard system
from utils.dashboard import DashboardUI, AnalysisConfig, FilterConfig, ThresholdConfig

# Import existing functions from data_processing
from .data_processing import (
    interactive_channel_mapping_selection,
    interactive_folder_selection, 
    interactive_threshold_selection,
    interactive_filter_selection,
    clear_screen
)

# Import file scanning from main script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def scan_for_csv_files(directory):
    """
    Scan a directory for CSV files and return a list of found files.
    (Copied from main script for integration)
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


class DashboardController:
    """Controller for managing dashboard workflow"""
    
    def __init__(self):
        self.dashboard = DashboardUI()
        self.csv_files_cache = None
    
    def get_csv_files(self) -> List[str]:
        """Get available CSV files from current directory"""
        if self.csv_files_cache is None:
            current_dir = os.getcwd()
            self.csv_files_cache = scan_for_csv_files(current_dir)
        return self.csv_files_cache
    
    def handle_file_selection(self) -> bool:
        """Handle file selection using the original file selection logic"""
        from datetime import datetime
        
        clear_screen()
        
        current_dir = os.getcwd()
        print(f"\nScanning for CSV files in: {current_dir}")
        
        csv_files = self.get_csv_files()
        
        if not csv_files:
            print("No CSV files found in the current directory.")
            input("Press Enter to continue...")
            return False
        
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
        print("\nSelect files to process:")
        print("• Single file: Enter number (e.g., 3)")
        print("• Multiple files: Enter comma-separated numbers (e.g., 1,3,4)")
        print("• All files: Enter 'all'")
        print("• Cancel: Enter 'c'")
        
        while True:
            try:
                choice = input(f"\nSelection: ").strip()
                
                if choice.lower() == 'c':
                    return False
                
                if choice.lower() == 'all':
                    self.dashboard.config.files = csv_files.copy()
                    print(f"\nSelected: All {len(csv_files)} files")
                    return True
                
                # Parse comma-separated list
                if ',' in choice:
                    try:
                        indices = [int(x.strip()) - 1 for x in choice.split(',')]
                        selected_files = []
                        
                        # Validate all indices
                        for idx in indices:
                            if not (0 <= idx < len(csv_files)):
                                print(f"Invalid file number: {idx + 1}. Please enter numbers between 1 and {len(csv_files)}")
                                break
                        else:
                            # All indices are valid
                            for idx in indices:
                                selected_files.append(csv_files[idx])
                            
                            self.dashboard.config.files = selected_files
                            print(f"\nSelected {len(selected_files)} files")
                            return True
                            
                    except ValueError:
                        print("Invalid format. Use comma-separated numbers (e.g., 1,3,4)")
                        continue
                else:
                    # Single file selection
                    file_index = int(choice) - 1
                    
                    if 0 <= file_index < len(csv_files):
                        selected_file = csv_files[file_index]
                        self.dashboard.config.files = [selected_file]
                        filename = os.path.basename(selected_file)
                        print(f"\nSelected: {filename}")
                        return True
                    else:
                        print(f"Please enter a number between 1 and {len(csv_files)}")
                        
            except ValueError:
                print("Please enter a valid number, comma-separated numbers, 'all', or 'c' to cancel")
            except KeyboardInterrupt:
                return False
    
    def handle_output_folder(self) -> bool:
        """Handle output folder selection"""
        result = interactive_folder_selection()
        if result is not None:
            self.dashboard.config.output_folder = result
            return True
        return False
    
    def handle_channel_mapping(self) -> bool:
        """Handle channel mapping selection"""
        result = interactive_channel_mapping_selection()
        if result is not None:
            if result == "none":
                self.dashboard.config.use_channel_mapping = False
                self.dashboard.config.channel_mapping_file = None
            else:
                self.dashboard.config.use_channel_mapping = True
                self.dashboard.config.channel_mapping_file = result
            return True
        return False
    
    def handle_filtering(self) -> bool:
        """Handle signal filtering configuration"""
        result = self.interactive_filter_selection_v2()
        if result is not None:
            # Convert the result to our FilterConfig format
            self.dashboard.config.filtering = FilterConfig(
                lowpass_enabled=result.get('lowpass_enabled', False),
                notch_enabled=result.get('notch_enabled', False),
                sampling_rate=result.get('sampling_rate', 1000.0),
                lowpass_cutoff=result.get('lowpass_cutoff', 50.0),
                notch_freq=result.get('notch_freq', 60.0),
                notch_q=result.get('notch_q', 30.0)
            )
            return True
        return False
    
    def interactive_filter_selection_v2(self):
        """Interactive filter configuration with independent controls"""
        print(f"\n{Fore.CYAN}═══ SIGNAL FILTERING CONFIGURATION ═══{Style.RESET_ALL}")
        
        current_config = self.dashboard.config.filtering
        
        print(f"\nCurrent Configuration:")
        print(f"  Low-pass Filter: {'ENABLED' if current_config.lowpass_enabled else 'DISABLED'}")
        if current_config.lowpass_enabled:
            print(f"    Cutoff: {current_config.lowpass_cutoff} Hz")
        print(f"  Notch Filter: {'ENABLED' if current_config.notch_enabled else 'DISABLED'}")
        if current_config.notch_enabled:
            print(f"    Frequency: {current_config.notch_freq} Hz, Q: {current_config.notch_q}")
        print(f"  Sampling Rate: {current_config.sampling_rate} Hz")
        
        print(f"\nOptions:")
        print(f"  1. Toggle Low-pass Filter")
        print(f"  2. Toggle Notch Filter")
        print(f"  3. Configure Low-pass Settings (Cutoff Frequency)")
        print(f"  4. Configure Notch Settings (Frequency & Q Factor)")
        print(f"  5. Configure Sampling Rate")
        print(f"  6. Apply Settings")
        print(f"  0. Cancel")
        
        while True:
            try:
                choice = input(f"\n{Fore.CYAN}Select option (0-6): {Style.RESET_ALL}").strip()
                
                if choice == '0':
                    return None
                elif choice == '1':
                    current_config.lowpass_enabled = not current_config.lowpass_enabled
                    status = "ENABLED" if current_config.lowpass_enabled else "DISABLED"
                    print(f"Low-pass filter {status}")
                elif choice == '2':
                    current_config.notch_enabled = not current_config.notch_enabled
                    status = "ENABLED" if current_config.notch_enabled else "DISABLED"
                    print(f"Notch filter {status}")
                elif choice == '3':
                    # Configure low-pass settings (enable filter if not already enabled)
                    try:
                        cutoff = float(input(f"Enter low-pass cutoff frequency (current: {current_config.lowpass_cutoff} Hz): "))
                        if cutoff > 0:
                            current_config.lowpass_cutoff = cutoff
                            if not current_config.lowpass_enabled:
                                current_config.lowpass_enabled = True
                                print(f"Low-pass filter ENABLED and set to {cutoff} Hz")
                            else:
                                print(f"Low-pass filter updated to {cutoff} Hz")
                        else:
                            print("Please enter a positive frequency")
                    except ValueError:
                        print("Please enter a valid number")
                elif choice == '4':
                    # Configure notch settings (enable filter if not already enabled)
                    try:
                        freq = float(input(f"Enter notch frequency (current: {current_config.notch_freq} Hz): "))
                        q = float(input(f"Enter quality factor (current: {current_config.notch_q}): "))
                        if freq > 0 and q > 0:
                            current_config.notch_freq = freq
                            current_config.notch_q = q
                            if not current_config.notch_enabled:
                                current_config.notch_enabled = True
                                print(f"Notch filter ENABLED and set to {freq} Hz, Q={q}")
                            else:
                                print(f"Notch filter updated to {freq} Hz, Q={q}")
                        else:
                            print("Please enter positive values")
                    except ValueError:
                        print("Please enter valid numbers")
                elif choice == '5':
                    try:
                        rate = float(input(f"Enter sampling rate (current: {current_config.sampling_rate} Hz): "))
                        if rate > 0:
                            current_config.sampling_rate = rate
                            print(f"Sampling rate set to {rate} Hz")
                        else:
                            print("Please enter a positive sampling rate")
                    except ValueError:
                        print("Please enter a valid number")
                elif choice == '6':
                    return {
                        'lowpass_enabled': current_config.lowpass_enabled,
                        'notch_enabled': current_config.notch_enabled,
                        'sampling_rate': current_config.sampling_rate,
                        'lowpass_cutoff': current_config.lowpass_cutoff,
                        'notch_freq': current_config.notch_freq,
                        'notch_q': current_config.notch_q
                    }
                else:
                    print("Please enter a number between 0 and 6")
                    
                # Show updated status
                print(f"\nUpdated Configuration:")
                print(f"  Low-pass: {'ENABLED' if current_config.lowpass_enabled else 'DISABLED'}")
                if current_config.lowpass_enabled:
                    print(f"    Cutoff: {current_config.lowpass_cutoff} Hz")
                print(f"  Notch: {'ENABLED' if current_config.notch_enabled else 'DISABLED'}")
                if current_config.notch_enabled:
                    print(f"    Frequency: {current_config.notch_freq} Hz, Q: {current_config.notch_q}")
                    
            except KeyboardInterrupt:
                return None
    
    def handle_thresholds(self) -> bool:
        """Handle threshold configuration"""
        result = interactive_threshold_selection()
        if result is not None:
            self.dashboard.config.thresholds = ThresholdConfig(
                low_thresh=result['low_thresh'],
                high_thresh=result['high_thresh'],
                low_amplitude_thresh=result['low_amplitude_thresh']
            )
            return True
        return False
    
    def run_main_dashboard(self) -> Optional[AnalysisConfig]:
        """Run the main dashboard and return final configuration"""
        
        while True:
            self.dashboard.display_dashboard()
            choice = self.dashboard.get_user_choice()
            
            if choice == 'q':
                return None
            
            elif choice == 'f':
                self.handle_file_selection()
            
            elif choice == '1':  # Output folder
                self.handle_output_folder()
            
            elif choice == '2':  # Channel mapping
                self.handle_channel_mapping()
            
            elif choice == '3':  # Signal filtering
                self.handle_filtering()
            
            elif choice == '4':  # Thresholds
                self.handle_thresholds()
            
            elif choice == 'd':  # Load defaults
                self.dashboard.load_defaults()
            
            elif choice == 's':  # Save preset
                self.dashboard.interactive_save_preset()
                input("Press Enter to continue...")
            
            elif choice == 'l':  # Load preset
                presets = self.dashboard.list_presets()
                if presets:
                    print("Available presets:")
                    for i, preset in enumerate(presets, 1):
                        print(f"  {i}. {preset}")
                    try:
                        preset_choice = input("Enter preset number or name: ").strip()
                        if preset_choice.isdigit():
                            preset_idx = int(preset_choice) - 1
                            if 0 <= preset_idx < len(presets):
                                self.dashboard.load_preset(presets[preset_idx])
                        else:
                            self.dashboard.load_preset(preset_choice)
                    except (ValueError, KeyboardInterrupt):
                        pass
                    input("Press Enter to continue...")
                else:
                    print("No presets available.")
                    input("Press Enter to continue...")
            
            elif choice == 'x':  # Delete preset
                self.dashboard.interactive_delete_preset()
            
            elif choice == 'm':  # Rename preset
                self.dashboard.interactive_rename_preset()
            
            elif choice == 'r':  # Run analysis
                is_valid, errors = self.dashboard.config.is_valid()
                if is_valid:
                    return self.dashboard.config
                else:
                    print(f"\nPlease fix the following issues first:")
                    for error in errors:
                        print(f"  • {error}")
                    input("Press Enter to continue...")