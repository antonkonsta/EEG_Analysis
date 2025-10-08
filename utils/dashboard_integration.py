#!/usr/bin/env python3
"""
Dashboard Integration for EEG Analysis

This module provides the integration layer between the dashboard UI
and the existing EEG analysis functions.
"""

import os
import sys
from typing import List, Optional, Tuple

# Import the dashboard system
from .dashboard import DashboardUI, AnalysisConfig, FilterConfig, ThresholdConfig

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
        result = interactive_filter_selection()
        if result is not None:
            # Convert the result to our FilterConfig format
            self.dashboard.config.filtering = FilterConfig(
                enabled=result.get('apply_filtering', False),
                sampling_rate=result.get('sampling_rate', 1000.0),
                lowpass_cutoff=result.get('lowpass_cutoff', 50.0),
                notch_freq=result.get('notch_freq', 60.0),
                notch_q=result.get('notch_q', 30.0)
            )
            return True
        return False
    
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
                preset_name = input("Enter preset name: ").strip()
                if preset_name:
                    self.dashboard.save_preset(preset_name)
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