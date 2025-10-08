#!/usr/bin/env python3
"""
EEG Analysis Dashboard System

Cross-platform terminal dashboard for configuring and running EEG analysis.
Uses ASCII art and colorama for cross-platform compatibility.
"""

import os
import sys
import json
import platform
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

try:
    import colorama
    from colorama import Fore, Back, Style, init
    # Initialize colorama for cross-platform colored output
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not available
    COLORS_AVAILABLE = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = BLACK = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""


@dataclass
class FilterConfig:
    """Configuration for signal filtering"""
    enabled: bool = False
    sampling_rate: float = 1000.0
    lowpass_cutoff: float = 50.0
    notch_freq: float = 60.0
    notch_q: float = 30.0
    
    def __str__(self):
        if self.enabled:
            return f"ENABLED (Low-pass: {self.lowpass_cutoff}Hz, Notch: {self.notch_freq}Hz)"
        return "DISABLED"


@dataclass
class ThresholdConfig:
    """Configuration for analysis thresholds"""
    low_thresh: float = 0.053
    high_thresh: float = 3.247
    low_amplitude_thresh: float = 0.5
    
    def __str__(self):
        return f"Low: {self.low_thresh}V, High: {self.high_thresh}V, Amp: {self.low_amplitude_thresh}mV"


@dataclass
class AnalysisConfig:
    """Complete configuration for EEG analysis"""
    files: List[str] = None
    output_folder: str = "default"
    channel_mapping_file: Optional[str] = None
    use_channel_mapping: bool = True
    filtering: FilterConfig = None
    thresholds: ThresholdConfig = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.filtering is None:
            self.filtering = FilterConfig()
        if self.thresholds is None:
            self.thresholds = ThresholdConfig()
    
    def is_valid(self) -> tuple[bool, List[str]]:
        """Validate configuration and return status with any error messages"""
        errors = []
        
        if not self.files:
            errors.append("No files selected")
        
        for file_path in self.files:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {os.path.basename(file_path)}")
        
        if self.use_channel_mapping and self.channel_mapping_file:
            if not os.path.exists(self.channel_mapping_file):
                errors.append("Channel mapping file not found")
        
        return len(errors) == 0, errors
    
    def get_file_summary(self) -> str:
        """Get a summary of selected files"""
        if not self.files:
            return "No files selected"
        
        if len(self.files) == 1:
            return f"1 file: {os.path.basename(self.files[0])}"
        elif len(self.files) <= 3:
            names = [os.path.basename(f) for f in self.files]
            return f"{len(self.files)} files: {', '.join(names)}"
        else:
            first_few = [os.path.basename(f) for f in self.files[:2]]
            return f"{len(self.files)} files: {', '.join(first_few)}, ..."


class DashboardUI:
    """Cross-platform terminal dashboard UI"""
    
    def __init__(self):
        self.config = AnalysisConfig()
        self.presets_dir = os.path.join(os.path.dirname(__file__), '..', 'presets')
        os.makedirs(self.presets_dir, exist_ok=True)
    
    def clear_screen(self):
        """Clear terminal screen (cross-platform)"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_terminal_width(self) -> int:
        """Get terminal width (cross-platform)"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback
    
    def print_header(self):
        """Print the dashboard header"""
        width = min(self.get_terminal_width(), 100)
        title = "EEG ANALYSIS DASHBOARD"
        
        print(f"{Fore.CYAN}{Style.BRIGHT}╔{'═' * (width - 2)}╗")
        print(f"║{title.center(width - 2)}║")
        print(f"╠{'═' * (width - 2)}╣{Style.RESET_ALL}")
    
    def print_footer(self):
        """Print the dashboard footer"""
        width = min(self.get_terminal_width(), 100)
        print(f"{Fore.CYAN}╚{'═' * (width - 2)}╝{Style.RESET_ALL}")
    
    def print_files_section(self):
        """Print the files section"""
        file_summary = self.config.get_file_summary()
        is_valid, _ = self.config.is_valid()
        
        status_color = Fore.GREEN if self.config.files else Fore.YELLOW
        status_icon = "✓" if self.config.files else "⚠"
        
        print(f"║ {status_color}{status_icon} FILES: {file_summary:<50} [F] Change ║{Style.RESET_ALL}")
    
    def print_config_section(self):
        """Print the configuration overview section"""
        print(f"║ {Fore.WHITE}{Style.BRIGHT}CONFIGURATION OVERVIEW:{' ' * 52}║{Style.RESET_ALL}")
        
        # Output folder
        folder_display = self.config.output_folder if self.config.output_folder != "default" else "Default location"
        print(f"║   📁 Output Folder: {folder_display:<35} [1] Change ║")
        
        # Channel mapping
        if self.config.use_channel_mapping and self.config.channel_mapping_file:
            mapping_name = os.path.basename(self.config.channel_mapping_file)
            mapping_display = f"Enabled ({mapping_name})"
            mapping_color = Fore.GREEN
        elif self.config.use_channel_mapping:
            mapping_display = "Enabled (default)"
            mapping_color = Fore.GREEN
        else:
            mapping_display = "Disabled"
            mapping_color = Fore.YELLOW
        
        print(f"║   🗺️  Channel Mapping: {mapping_color}{mapping_display:<30}{Style.RESET_ALL} [2] Change ║")
        
        # Signal filtering
        filter_color = Fore.GREEN if self.config.filtering.enabled else Fore.YELLOW
        print(f"║   ⚡ Signal Filtering: {filter_color}{str(self.config.filtering):<30}{Style.RESET_ALL} [3] Change ║")
        
        # Thresholds
        print(f"║   📊 Thresholds: {Fore.GREEN}{str(self.config.thresholds):<35}{Style.RESET_ALL} [4] Change ║")
    
    def print_actions_section(self):
        """Print the quick actions section"""
        print(f"║ {' ' * 76} ║")
        print(f"║ {Fore.WHITE}{Style.BRIGHT}QUICK ACTIONS:{' ' * 61}║{Style.RESET_ALL}")
        
        # Check if ready to run
        is_valid, errors = self.config.is_valid()
        if is_valid:
            run_color = Fore.GREEN
            run_text = "[R] Run Analysis"
        else:
            run_color = Fore.RED
            run_text = "[R] Run (Fix errors first)"
        
        print(f"║   [F] Files    {run_color}{run_text:<20}{Style.RESET_ALL} [D] Load Defaults ║")
        print(f"║   [S] Save Preset      [L] Load Preset         [Q] Quit      ║")
    
    def print_status_section(self):
        """Print validation status and warnings"""
        is_valid, errors = self.config.is_valid()
        
        if errors:
            print(f"║ {' ' * 76} ║")
            print(f"║ {Fore.RED}{Style.BRIGHT}⚠ ISSUES TO FIX:{' ' * 59}║{Style.RESET_ALL}")
            for error in errors[:3]:  # Show max 3 errors
                print(f"║   {Fore.RED}• {error:<70}{Style.RESET_ALL} ║")
        else:
            print(f"║ {Fore.GREEN}✓ Configuration ready - all settings validated{' ' * 27}║{Style.RESET_ALL}")
    
    def display_dashboard(self):
        """Display the complete dashboard"""
        self.clear_screen()
        self.print_header()
        self.print_files_section()
        print(f"║ {'─' * 76} ║")
        self.print_config_section()
        print(f"║ {'─' * 76} ║")
        self.print_actions_section()
        print(f"║ {'─' * 76} ║")
        self.print_status_section()
        self.print_footer()
    
    def get_user_choice(self) -> str:
        """Get user input with validation"""
        valid_choices = ['1', '2', '3', '4', 'f', 'r', 'd', 's', 'l', 'q']
        
        while True:
            try:
                choice = input(f"\n{Fore.CYAN}Enter choice (1-4, F, R, D, S, L, Q): {Style.RESET_ALL}").strip().lower()
                
                if choice in valid_choices:
                    return choice
                else:
                    print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                return 'q'
    
    def save_preset(self, name: str):
        """Save current configuration as a preset"""
        preset_file = os.path.join(self.presets_dir, f"{name}.json")
        
        # Convert dataclasses to dict for JSON serialization
        config_dict = {
            'files': self.config.files,
            'output_folder': self.config.output_folder,
            'channel_mapping_file': self.config.channel_mapping_file,
            'use_channel_mapping': self.config.use_channel_mapping,
            'filtering': asdict(self.config.filtering),
            'thresholds': asdict(self.config.thresholds),
            'created': datetime.now().isoformat(),
            'platform': platform.system()
        }
        
        try:
            with open(preset_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            print(f"{Fore.GREEN}Preset '{name}' saved successfully!{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving preset: {e}{Style.RESET_ALL}")
    
    def load_preset(self, name: str) -> bool:
        """Load a configuration preset"""
        preset_file = os.path.join(self.presets_dir, f"{name}.json")
        
        if not os.path.exists(preset_file):
            print(f"{Fore.RED}Preset '{name}' not found.{Style.RESET_ALL}")
            return False
        
        try:
            with open(preset_file, 'r') as f:
                config_dict = json.load(f)
            
            # Reconstruct configuration
            self.config.files = config_dict.get('files', [])
            self.config.output_folder = config_dict.get('output_folder', 'default')
            self.config.channel_mapping_file = config_dict.get('channel_mapping_file')
            self.config.use_channel_mapping = config_dict.get('use_channel_mapping', True)
            
            # Reconstruct filtering config
            filter_data = config_dict.get('filtering', {})
            self.config.filtering = FilterConfig(**filter_data)
            
            # Reconstruct threshold config
            threshold_data = config_dict.get('thresholds', {})
            self.config.thresholds = ThresholdConfig(**threshold_data)
            
            print(f"{Fore.GREEN}Preset '{name}' loaded successfully!{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}Error loading preset: {e}{Style.RESET_ALL}")
            return False
    
    def list_presets(self) -> List[str]:
        """List available presets"""
        try:
            presets = []
            for file in os.listdir(self.presets_dir):
                if file.endswith('.json'):
                    presets.append(file[:-5])  # Remove .json extension
            return sorted(presets)
        except:
            return []
    
    def load_defaults(self):
        """Load default configuration"""
        self.config = AnalysisConfig()
        print(f"{Fore.GREEN}Default configuration loaded.{Style.RESET_ALL}")


def test_dashboard():
    """Test function to demo the dashboard"""
    dashboard = DashboardUI()
    
    # Add some test data
    dashboard.config.files = [
        "/path/to/anthonyDRL300k_2.csv",
        "/path/to/hollemanDRL200k_3.csv"
    ]
    dashboard.config.filtering.enabled = True
    
    print("Testing dashboard display...")
    dashboard.display_dashboard()
    print(f"\n{Fore.GREEN}Dashboard test completed successfully!{Style.RESET_ALL}")
    print("This was just a display test. Integration with main script pending.")


if __name__ == "__main__":
    test_dashboard()