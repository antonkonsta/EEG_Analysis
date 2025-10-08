"""
Data processing utilities for EEG analysis pipeline.

This module contains functions for file handling, folder organization,
and data preparation.
"""

import json
import subprocess
import platform
import os


def clear_screen():
    """
    Clear the terminal screen for a cleaner interface.
    """
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')


def open_pdf_file(pdf_path):
    """
    Open a PDF file using the system's default PDF viewer.
    
    Args:
        pdf_path (str): Path to the PDF file to open
    """
    try:
        if platform.system() == 'Windows':
            # Windows
            subprocess.run(['start', '', pdf_path], shell=True, check=True)
        elif platform.system() == 'Darwin':
            # macOS
            subprocess.run(['open', pdf_path], check=True)
        else:
            # Linux and other Unix-like systems
            subprocess.run(['xdg-open', pdf_path], check=True)
        
        print(f"Opening PDF: {os.path.basename(pdf_path)}")
    except subprocess.CalledProcessError:
        print(f"Could not automatically open PDF. Please manually open: {pdf_path}")
    except Exception as e:
        print(f"Error opening PDF: {e}")
        print(f"Please manually open: {pdf_path}")


def load_filter_preferences():
    """
    Load previously saved filter preferences from file.
    
    Returns:
        dict: Dictionary containing filter values, or defaults if no saved preferences
    """
    # Find the base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    preferences_file = os.path.join(base_dir, ".filter_preferences.json")
    
    # Default values
    defaults = {
        'apply_filtering': False,
        'lowpass_cutoff': 40.0,
        'notch_freq': 60.0,
        'notch_q': 30.0,
        'sampling_rate': 500.0  # Default sampling rate
    }
    
    try:
        if os.path.exists(preferences_file):
            with open(preferences_file, 'r') as f:
                saved_prefs = json.load(f)
                # Merge with defaults in case new parameters are added
                defaults.update(saved_prefs)
                return defaults
    except (json.JSONDecodeError, PermissionError, KeyError):
        pass  # Use defaults if file is corrupted or unreadable
    
    return defaults


def save_filter_preferences(apply_filtering, lowpass_cutoff, notch_freq, notch_q, sampling_rate):
    """
    Save filter preferences to file for next run.
    
    Args:
        apply_filtering (bool): Whether to apply filtering
        lowpass_cutoff (float): Low-pass filter cutoff frequency in Hz
        notch_freq (float): Notch filter frequency in Hz
        notch_q (float): Notch filter quality factor
        sampling_rate (float): Sampling rate in Hz
    """
    # Find the base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    preferences_file = os.path.join(base_dir, ".filter_preferences.json")
    
    preferences = {
        'apply_filtering': apply_filtering,
        'lowpass_cutoff': lowpass_cutoff,
        'notch_freq': notch_freq,
        'notch_q': notch_q,
        'sampling_rate': sampling_rate
    }
    
    try:
        with open(preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
    except PermissionError:
        print("Warning: Could not save filter preferences (permission denied)")


def interactive_filter_selection():
    """
    Interactively configure signal filtering with saved preferences.
    
    Returns:
        dict: Dictionary containing selected filter configuration
    """
    clear_screen()
    
    # Load saved preferences or defaults
    current_prefs = load_filter_preferences()
    
    print(f"\nSignal Filtering Configuration:")
    print("-" * 60)
    print("Current settings (from last run or defaults):")
    print(f"  Apply filtering: {'Yes' if current_prefs['apply_filtering'] else 'No'}")
    if current_prefs['apply_filtering']:
        print(f"  Low-pass cutoff: {current_prefs['lowpass_cutoff']} Hz")
        print(f"  Notch frequency: {current_prefs['notch_freq']} Hz")
        print(f"  Notch Q factor: {current_prefs['notch_q']}")
        print(f"  Sampling rate: {current_prefs['sampling_rate']} Hz")
    print("-" * 60)
    print("1. Use current settings")
    print("2. No filtering (use raw data)")
    print("3. Apply standard filtering (40Hz low-pass + 60Hz notch)")
    print("4. Custom filter settings")
    print("-" * 60)
    
    while True:
        try:
            choice = input("Select option (1-4) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if choice_num == 1:
                # Use current settings
                print("Using current filter settings.")
                return current_prefs
                
            elif choice_num == 2:
                # No filtering
                new_prefs = current_prefs.copy()
                new_prefs['apply_filtering'] = False
                save_filter_preferences(
                    new_prefs['apply_filtering'],
                    new_prefs['lowpass_cutoff'],
                    new_prefs['notch_freq'],
                    new_prefs['notch_q'],
                    new_prefs['sampling_rate']
                )
                print("No filtering will be applied (raw data).")
                return new_prefs
                
            elif choice_num == 3:
                # Standard filtering
                new_prefs = current_prefs.copy()
                new_prefs['apply_filtering'] = True
                new_prefs['lowpass_cutoff'] = 40.0
                new_prefs['notch_freq'] = 60.0
                new_prefs['notch_q'] = 30.0
                
                # Get sampling rate
                while True:
                    try:
                        current_fs = new_prefs['sampling_rate']
                        response = input(f"Sampling rate ({current_fs} Hz): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0:
                            print("Sampling rate must be greater than 0")
                            continue
                        new_prefs['sampling_rate'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                save_filter_preferences(
                    new_prefs['apply_filtering'],
                    new_prefs['lowpass_cutoff'],
                    new_prefs['notch_freq'],
                    new_prefs['notch_q'],
                    new_prefs['sampling_rate']
                )
                
                print("\nStandard filtering settings saved:")
                print(f"  Low-pass cutoff: {new_prefs['lowpass_cutoff']} Hz")
                print(f"  Notch frequency: {new_prefs['notch_freq']} Hz")
                print(f"  Notch Q factor: {new_prefs['notch_q']}")
                print(f"  Sampling rate: {new_prefs['sampling_rate']} Hz")
                
                return new_prefs
                
            elif choice_num == 4:
                # Custom filter settings
                new_prefs = current_prefs.copy()
                new_prefs['apply_filtering'] = True
                
                print(f"\nCustom filter configuration:")
                print("(Press Enter to keep current value)")
                
                # Sampling rate
                while True:
                    try:
                        current_val = new_prefs['sampling_rate']
                        response = input(f"Sampling rate ({current_val} Hz): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0:
                            print("Sampling rate must be greater than 0")
                            continue
                        new_prefs['sampling_rate'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # Low-pass cutoff
                while True:
                    try:
                        current_val = new_prefs['lowpass_cutoff']
                        response = input(f"Low-pass cutoff frequency ({current_val} Hz): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0 or new_val >= new_prefs['sampling_rate'] / 2:
                            print(f"Cutoff must be between 0 and {new_prefs['sampling_rate'] / 2} Hz (Nyquist)")
                            continue
                        new_prefs['lowpass_cutoff'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # Notch frequency
                while True:
                    try:
                        current_val = new_prefs['notch_freq']
                        response = input(f"Notch frequency ({current_val} Hz): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0 or new_val >= new_prefs['sampling_rate'] / 2:
                            print(f"Notch frequency must be between 0 and {new_prefs['sampling_rate'] / 2} Hz (Nyquist)")
                            continue
                        new_prefs['notch_freq'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # Notch Q factor
                while True:
                    try:
                        current_val = new_prefs['notch_q']
                        response = input(f"Notch Q factor ({current_val}): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0:
                            print("Q factor must be greater than 0")
                            continue
                        new_prefs['notch_q'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                save_filter_preferences(
                    new_prefs['apply_filtering'],
                    new_prefs['lowpass_cutoff'],
                    new_prefs['notch_freq'],
                    new_prefs['notch_q'],
                    new_prefs['sampling_rate']
                )
                
                print("\nCustom filter settings saved:")
                print(f"  Low-pass cutoff: {new_prefs['lowpass_cutoff']} Hz")
                print(f"  Notch frequency: {new_prefs['notch_freq']} Hz")
                print(f"  Notch Q factor: {new_prefs['notch_q']}")
                print(f"  Sampling rate: {new_prefs['sampling_rate']} Hz")
                
                return new_prefs
            else:
                print("Please enter 1, 2, 3, or 4")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def load_threshold_preferences():
    """
    Load previously saved threshold preferences from file.
    
    Returns:
        dict: Dictionary containing threshold values, or defaults if no saved preferences
    """
    # Find the base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    preferences_file = os.path.join(base_dir, ".threshold_preferences.json")
    
    # Default values
    defaults = {
        'low_amplitude_thresh': 0.5,
        'low_thresh': 0.053,
        'high_thresh': 3.247
    }
    
    try:
        if os.path.exists(preferences_file):
            with open(preferences_file, 'r') as f:
                saved_prefs = json.load(f)
                # Merge with defaults in case new parameters are added
                defaults.update(saved_prefs)
                return defaults
    except (json.JSONDecodeError, PermissionError, KeyError):
        pass  # Use defaults if file is corrupted or unreadable
    
    return defaults


def save_threshold_preferences(low_amplitude_thresh, low_thresh, high_thresh):
    """
    Save threshold preferences to file for next run.
    
    Args:
        low_amplitude_thresh (float): Low amplitude threshold in mV
        low_thresh (float): Low saturation threshold in V
        high_thresh (float): High saturation threshold in V
    """
    # Find the base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    preferences_file = os.path.join(base_dir, ".threshold_preferences.json")
    
    preferences = {
        'low_amplitude_thresh': low_amplitude_thresh,
        'low_thresh': low_thresh,
        'high_thresh': high_thresh
    }
    
    try:
        with open(preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
    except PermissionError:
        print("Warning: Could not save threshold preferences (permission denied)")


def interactive_threshold_selection():
    """
    Interactively configure threshold values with saved preferences.
    
    Returns:
        dict: Dictionary containing selected threshold values
    """
    clear_screen()
    
    # Load saved preferences or defaults
    current_prefs = load_threshold_preferences()
    
    print(f"\nThreshold Configuration:")
    print("-" * 60)
    print("Current settings (from last run or defaults):")
    print(f"  Low amplitude threshold: {current_prefs['low_amplitude_thresh']} mV")
    print(f"  Low saturation threshold: {current_prefs['low_thresh']} V")
    print(f"  High saturation threshold: {current_prefs['high_thresh']} V")
    print("-" * 60)
    print("1. Use current settings (recommended)")
    print("2. Modify threshold values")
    print("-" * 60)
    
    while True:
        try:
            choice = input("Select option (1-2) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if choice_num == 1:
                # Use current settings
                print("Using current threshold settings.")
                return current_prefs
                
            elif choice_num == 2:
                # Modify thresholds
                new_prefs = current_prefs.copy()
                
                print(f"\nModifying threshold values:")
                print("(Press Enter to keep current value)")
                
                # Low amplitude threshold
                while True:
                    try:
                        current_val = new_prefs['low_amplitude_thresh']
                        response = input(f"Low amplitude threshold ({current_val} mV): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0:
                            print("Threshold must be greater than 0")
                            continue
                        new_prefs['low_amplitude_thresh'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # Low saturation threshold
                while True:
                    try:
                        current_val = new_prefs['low_thresh']
                        response = input(f"Low saturation threshold ({current_val} V): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= 0:
                            print("Threshold must be greater than 0")
                            continue
                        new_prefs['low_thresh'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # High saturation threshold
                while True:
                    try:
                        current_val = new_prefs['high_thresh']
                        response = input(f"High saturation threshold ({current_val} V): ").strip()
                        if not response:
                            break  # Keep current value
                        
                        new_val = float(response)
                        if new_val <= new_prefs['low_thresh']:
                            print("High threshold must be greater than low threshold")
                            continue
                        new_prefs['high_thresh'] = new_val
                        break
                    except ValueError:
                        print("Please enter a valid number")
                
                # Save the new preferences
                save_threshold_preferences(
                    new_prefs['low_amplitude_thresh'],
                    new_prefs['low_thresh'], 
                    new_prefs['high_thresh']
                )
                
                print("\nNew threshold settings saved:")
                print(f"  Low amplitude threshold: {new_prefs['low_amplitude_thresh']} mV")
                print(f"  Low saturation threshold: {new_prefs['low_thresh']} V")
                print(f"  High saturation threshold: {new_prefs['high_thresh']} V")
                
                return new_prefs
            else:
                print("Please enter 1 or 2")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


import os
import shutil
from datetime import datetime


def setup_output_folders(csv_file, output_pdf=None, custom_folder_path=None):
    """
    Create folder structure and determine output paths.
    
    Parameters:
        csv_file (str): Path to the input CSV file
        output_pdf (str): Optional output PDF filename
        custom_folder_path (str): Optional custom folder path to use instead of date-based
        
    Returns:
        dict: Dictionary containing output paths
    """
    if custom_folder_path:
        # Use the provided custom folder path
        output_folder = custom_folder_path
    else:
        # Create date-based folder structure (default behavior)
        current_date = datetime.now().strftime("%Y-%m-%d")
        script_dir = os.path.dirname(os.path.abspath(csv_file))
        
        # Look for the generate_channel_report.py script to find the correct base directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
            parent = os.path.dirname(base_dir)
            if parent == base_dir:  # Reached root
                base_dir = os.path.dirname(csv_file)
                break
            base_dir = parent
        
        reports_dir = os.path.join(base_dir, "reports")
        output_folder = os.path.join(reports_dir, current_date)
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get the base name of the CSV file
    csv_base_name = os.path.splitext(os.path.basename(csv_file))[0]
    
    # Default output filename (will be moved to output folder)
    if output_pdf is None:
        output_pdf = f"{csv_base_name}_channel_report.pdf"
    
    # Full path for the output PDF in the output folder
    output_pdf_path = os.path.join(output_folder, output_pdf)
    
    return {
        'pdf': output_pdf_path,
        'output_folder': output_folder,
        'csv_base_name': csv_base_name
    }


def move_source_csv(csv_file, output_folder):
    """
    Move the original CSV file to the output folder.
    
    Parameters:
        csv_file (str): Path to the source CSV file
        output_folder (str): Path to the output folder
    """
    csv_destination = os.path.join(output_folder, os.path.basename(csv_file))
    try:
        if not os.path.exists(csv_destination):
            shutil.move(csv_file, csv_destination)
            print(f"CSV file moved to: {csv_destination}")
        else:
            print(f"CSV file already exists in destination: {csv_destination}")
            # If destination exists, still remove the source to avoid duplicates
            if os.path.exists(csv_file):
                os.remove(csv_file)
                print(f"Removed duplicate source file: {csv_file}")
    except Exception as e:
        print(f"Warning: Could not move CSV file: {e}")


def interactive_channel_mapping_selection():
    """
    Interactively select a channel mapping file from the channel_mappings folder.
    
    Returns:
        str: Path to selected channel mapping file, or None if cancelled/not found
    """
    clear_screen()
    
    # Find the channel_mappings folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    channel_mappings_dir = os.path.join(base_dir, "channel_mappings")
    
    if not os.path.exists(channel_mappings_dir):
        print(f"Warning: Channel mappings folder not found at: {channel_mappings_dir}")
        return None
    
    # Scan for CSV files in channel_mappings folder
    mapping_files = []
    try:
        for file in os.listdir(channel_mappings_dir):
            if file.endswith('.csv') and os.path.isfile(os.path.join(channel_mappings_dir, file)):
                mapping_files.append(os.path.join(channel_mappings_dir, file))
    except PermissionError:
        print(f"Warning: No permission to read channel mappings directory")
        return None
    
    if not mapping_files:
        print("No channel mapping files found in the channel_mappings folder.")
        return None
    
    # Sort the files for consistent ordering
    mapping_files = sorted(mapping_files)
    
    # If only one mapping file, use it automatically
    if len(mapping_files) == 1:
        selected_file = mapping_files[0]
        filename = os.path.basename(selected_file)
        print(f"Using channel mapping: {filename}")
        return selected_file
    
    # Multiple files - let user choose
    print(f"\nFound {len(mapping_files)} channel mapping file(s):")
    print("-" * 60)
    
    for i, file_path in enumerate(mapping_files, 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Get file modification time
        mod_time = os.path.getmtime(file_path)
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        
        print(f"{i:2d}. {filename:<35} ({file_size} bytes, {mod_time_str})")
    
    print(f"{len(mapping_files)+1:2d}. No channel mapping (use raw channel names)")
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"\nSelect channel mapping (1-{len(mapping_files)+1}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if choice_num == len(mapping_files) + 1:
                print("No channel mapping selected - using raw channel names")
                return "none"
            elif 1 <= choice_num <= len(mapping_files):
                selected_file = mapping_files[choice_num - 1]
                filename = os.path.basename(selected_file)
                print(f"Selected channel mapping: {filename}")
                return selected_file
            else:
                print(f"Please enter a number between 1 and {len(mapping_files)+1}")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def interactive_folder_selection():
    """
    Interactively select where to save the report.
    
    Returns:
        str: Path to the selected folder, or None if cancelled
    """
    clear_screen()
    
    # Find the reports directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    # Look for the generate_channel_report.py script to find the correct base directory
    while base_dir and not os.path.exists(os.path.join(base_dir, "generate_channel_report.py")):
        parent = os.path.dirname(base_dir)
        if parent == base_dir:  # Reached root
            break
        base_dir = parent
    
    reports_dir = os.path.join(base_dir, "reports")
    
    print(f"\nSelect output folder option:")
    print("-" * 50)
    print("1. Date-based folder (default)")
    print("2. Create new custom folder")
    print("3. Use existing folder")
    print("-" * 50)
    
    while True:
        try:
            choice = input("Select option (1-3) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if choice_num == 1:
                # Default date-based folder
                today = datetime.now().strftime("%Y-%m-%d")
                date_folder = os.path.join(reports_dir, today)
                print(f"Using date-based folder: {today}")
                return date_folder
                
            elif choice_num == 2:
                # Custom folder name
                while True:
                    folder_name = input("Enter custom folder name: ").strip()
                    if not folder_name:
                        print("Please enter a folder name.")
                        continue
                    
                    # Clean folder name (remove invalid characters)
                    folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    if not folder_name:
                        print("Invalid folder name. Please use letters, numbers, spaces, hyphens, or underscores.")
                        continue
                    
                    custom_folder = os.path.join(reports_dir, folder_name)
                    print(f"Using custom folder: {folder_name}")
                    return custom_folder
                
            elif choice_num == 3:
                # Existing folder selection
                if not os.path.exists(reports_dir):
                    print("Reports directory doesn't exist yet. Creating date-based folder instead.")
                    today = datetime.now().strftime("%Y-%m-%d")
                    date_folder = os.path.join(reports_dir, today)
                    return date_folder
                
                # Get existing folders
                existing_folders = []
                try:
                    for item in os.listdir(reports_dir):
                        item_path = os.path.join(reports_dir, item)
                        if os.path.isdir(item_path):
                            existing_folders.append(item)
                except PermissionError:
                    print("No permission to read reports directory.")
                    return None
                
                if not existing_folders:
                    print("No existing folders found in reports directory.")
                    print("Creating date-based folder instead.")
                    today = datetime.now().strftime("%Y-%m-%d")
                    date_folder = os.path.join(reports_dir, today)
                    return date_folder
                
                # Sort folders (date folders first, then alphabetically)
                existing_folders.sort(reverse=True)
                
                print(f"\nFound {len(existing_folders)} existing folder(s):")
                print("-" * 60)
                
                for i, folder in enumerate(existing_folders, 1):
                    folder_path = os.path.join(reports_dir, folder)
                    
                    # Count files in folder
                    try:
                        file_count = len([f for f in os.listdir(folder_path) 
                                        if os.path.isfile(os.path.join(folder_path, f))])
                        
                        # Get folder modification time
                        mod_time = os.path.getmtime(folder_path)
                        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                        
                        print(f"{i:2d}. {folder:<25} ({file_count} files, {mod_time_str})")
                    except (PermissionError, OSError):
                        print(f"{i:2d}. {folder:<25} (access error)")
                
                print("-" * 60)
                
                while True:
                    try:
                        folder_choice = input(f"Select folder (1-{len(existing_folders)}) or 'b' to go back: ").strip()
                        
                        if folder_choice.lower() == 'b':
                            break  # Go back to main menu
                        
                        folder_choice_num = int(folder_choice)
                        
                        if 1 <= folder_choice_num <= len(existing_folders):
                            selected_folder_name = existing_folders[folder_choice_num - 1]
                            selected_folder = os.path.join(reports_dir, selected_folder_name)
                            print(f"Selected existing folder: {selected_folder_name}")
                            return selected_folder
                        else:
                            print(f"Please enter a number between 1 and {len(existing_folders)}")
                            
                    except ValueError:
                        print("Please enter a valid number or 'b' to go back")
                    except KeyboardInterrupt:
                        print("\nCancelled.")
                        return None
            else:
                print("Please enter 1, 2, or 3")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def get_default_output_filename(csv_file):
    """
    Generate the default output PDF filename based on the CSV filename.
    
    Parameters:
        csv_file (str): Path to the CSV file being processed
        
    Returns:
        str: The default output PDF filename (without path)
    """
    csv_base_name = os.path.splitext(os.path.basename(csv_file))[0]
    default_filename = f"{csv_base_name}_channel_report.pdf"
    return default_filename


def get_output_filename(csv_file, provided_filename=None):
    """
    Interactively get the output PDF filename from user input.
    
    Parameters:
        csv_file (str): Path to the CSV file being processed
        provided_filename (str): Filename provided via command line (optional)
        
    Returns:
        str: The output PDF filename (without path)
    """
    csv_base_name = os.path.splitext(os.path.basename(csv_file))[0]
    default_filename = f"{csv_base_name}_channel_report.pdf"
    
    # If filename was provided via command line, use it
    if provided_filename:
        return provided_filename
    
    clear_screen()
    
    print(f"\nProcessing: {os.path.basename(csv_file)}")
    print(f"Default output name: {default_filename}")
    
    try:
        user_input = input("Enter custom output filename (or press Enter for default): ").strip()
        
        if not user_input:
            print(f"Using default filename: {default_filename}")
            return default_filename
        
        # Ensure the filename has .pdf extension
        if not user_input.lower().endswith('.pdf'):
            user_input += '.pdf'
        
        print(f"Using custom filename: {user_input}")
        return user_input
        
    except KeyboardInterrupt:
        print(f"\nUsing default filename: {default_filename}")
        return default_filename


def validate_csv_file(csv_file):
    """
    Validate that the CSV file exists and is readable.
    
    Parameters:
        csv_file (str): Path to the CSV file
        
    Returns:
        str: Absolute path to the CSV file
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
    """
    csv_file = os.path.abspath(csv_file)
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Error: File '{csv_file}' not found")
    return csv_file