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

# Fix encoding issues on Windows
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # Try to enable UTF-8 mode on Windows console
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
    except:
        pass

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
        # More compact width as requested
        self.dashboard_width = 76  # Total width including borders
        self.content_width = self.dashboard_width - 4  # Account for "║ " and " ║" = 4 chars
        
        # Test if Unicode box drawing characters work
        self.use_unicode = self._test_unicode_support()
        
        # Box drawing characters
        if self.use_unicode:
            self.h_line = '═'
            self.v_line = '║'
            self.top_left = '╔'
            self.top_right = '╗'
            self.bottom_left = '╚'
            self.bottom_right = '╝'
            self.cross = '╣'
            self.cross_left = '╠'
            self.sep_line = '─'
        else:
            # ASCII fallback
            self.h_line = '='
            self.v_line = '|'
            self.top_left = '+'
            self.top_right = '+'
            self.bottom_left = '+'
            self.bottom_right = '+'
            self.cross = '+'
            self.cross_left = '+'
            self.sep_line = '-'
    
    def _test_unicode_support(self) -> bool:
        """Test if the terminal supports Unicode box drawing characters"""
        try:
            # Try to encode Unicode box drawing characters
            test_chars = '╔═╗║╚╝'
            test_chars.encode(sys.stdout.encoding or 'utf-8')
            return True
        except (UnicodeEncodeError, AttributeError):
            return False
    
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
    
    def strip_ansi_codes(self, text: str) -> str:
        """Remove ANSI color codes from text for accurate length measurement"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def get_visual_width(self, text: str) -> int:
        """Get the visual width of text as it appears in the terminal"""
        # Remove ANSI codes first
        clean_text = self.strip_ansi_codes(text)
        
        # Simple approach - no emoji complications
        return len(clean_text)
    
    def format_line_exact(self, left_content: str, right_content: str = "", left_colored: str = None) -> str:
        """Format a line with exact alignment using visual width calculation"""
        # Use colored version for display if provided
        display_left = left_colored if left_colored else left_content
        
        # Calculate visual widths using clean text
        left_width = self.get_visual_width(left_content)
        right_width = self.get_visual_width(right_content)
        
        # Total content that will be visible
        total_content_width = left_width + right_width
        
        # DEBUG: Print debug info for troubleshooting
        debug = False  # Set to True for debugging
        if debug:
            print(f"DEBUG: left='{left_content}' (w={left_width}), right='{right_content}' (w={right_width}), total={total_content_width}, content_width={self.content_width}")
        
        # Calculate exact padding needed
        if total_content_width >= self.content_width:
            # Content too long - truncate left side
            max_left = max(0, self.content_width - right_width - 3)  # 3 for "..."
            if max_left > 0:
                truncated_left = left_content[:max_left] + "..."
                display_left = truncated_left
            else:
                display_left = "..."
            padding_spaces = 0
        else:
            padding_spaces = self.content_width - total_content_width
        
        # Build the final line with exact spacing
        # Format: "║ {left_content}{padding}{right_content} ║"
        result = f"{self.v_line} {display_left}{' ' * padding_spaces}{right_content} {self.v_line}"
        
        # Verify length (for debugging)
        if debug:
            actual_length = len(self.strip_ansi_codes(result))
            expected_length = self.dashboard_width
            print(f"DEBUG: result length={actual_length}, expected={expected_length}")
        
        return result
    
    def print_header(self):
        """Print the dashboard header"""
        title = "EEG ANALYSIS DASHBOARD"
        
        # Use content_width + 2 for the horizontal lines to match content sections
        header_line_width = self.content_width + 2
        
        print(f"{Fore.CYAN}{Style.BRIGHT}{self.top_left}{self.h_line * header_line_width}{self.top_right}")
        
        # Format title line using same logic as content
        title_padding = (self.content_width - len(title)) // 2
        remaining_padding = self.content_width - len(title) - title_padding
        print(f"{self.v_line} {' ' * title_padding}{title}{' ' * remaining_padding} {self.v_line}")
        
        print(f"{self.cross_left}{self.h_line * header_line_width}{self.cross}{Style.RESET_ALL}")
    
    def print_footer(self):
        """Print the dashboard footer"""
        footer_line_width = self.content_width + 2
        print(f"{Fore.CYAN}{self.bottom_left}{self.h_line * footer_line_width}{self.bottom_right}{Style.RESET_ALL}")
    
    def print_files_section(self):
        """Print the files section"""
        file_summary = self.config.get_file_summary()
        
        status_color = Fore.GREEN if self.config.files else Fore.YELLOW
        status_icon = "OK" if self.config.files else "!"
        
        # Build the content with exact alignment
        left_content = f"{status_icon} FILES: {file_summary}"
        left_colored = f"{status_color}{status_icon} FILES: {file_summary}{Style.RESET_ALL}"
        right_content = "[F] Change"
        
        print(self.format_line_exact(left_content, right_content, left_colored))
    
    def print_config_section(self):
        """Print the configuration overview section"""
        # Section header
        header_content = "CONFIGURATION OVERVIEW:"
        colored_header = f"{Fore.WHITE}{Style.BRIGHT}{header_content}{Style.RESET_ALL}"
        print(self.format_line_exact(header_content, "", colored_header))
        
        # Output folder
        folder_display = self.config.output_folder if self.config.output_folder != "default" else "Default location"
        folder_content = f"  Output Folder: {folder_display}"
        print(self.format_line_exact(folder_content, "[1] Change"))
        
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
        
        mapping_content = f"  Channel Mapping: {mapping_display}"
        mapping_colored = f"  Channel Mapping: {mapping_color}{mapping_display}{Style.RESET_ALL}"
        print(self.format_line_exact(mapping_content, "[2] Change", mapping_colored))
        
        # Signal filtering
        filter_display = str(self.config.filtering)
        filter_color = Fore.GREEN if self.config.filtering.enabled else Fore.YELLOW
        filter_content = f"  Signal Filtering: {filter_display}"
        filter_colored = f"  Signal Filtering: {filter_color}{filter_display}{Style.RESET_ALL}"
        print(self.format_line_exact(filter_content, "[3] Change", filter_colored))
        
        # Thresholds
        threshold_display = str(self.config.thresholds)
        threshold_content = f"  Thresholds: {threshold_display}"
        threshold_colored = f"  Thresholds: {Fore.GREEN}{threshold_display}{Style.RESET_ALL}"
        print(self.format_line_exact(threshold_content, "[4] Change", threshold_colored))
    
    def print_actions_section(self):
        """Print the quick actions section"""
        # Empty line
        print(self.format_line_exact("", ""))
        
        # Section header
        header_content = "QUICK ACTIONS:"
        colored_header = f"{Fore.WHITE}{Style.BRIGHT}{header_content}{Style.RESET_ALL}"
        print(self.format_line_exact(header_content, "", colored_header))
        
        # Check if ready to run
        is_valid, errors = self.config.is_valid()
        if is_valid:
            run_color = Fore.GREEN
            run_text = "[R] Run Analysis"
        else:
            run_color = Fore.RED
            run_text = "[R] Run (Fix errors first)"
        
        # First action line
        action1_plain = f"  [F] Files    {run_text} [D] Load Defaults"
        action1_colored = f"  [F] Files    {run_color}{run_text}{Style.RESET_ALL} [D] Load Defaults"
        print(self.format_line_exact(action1_plain, "", action1_colored))
        
        # Second action line
        action2_content = "  [S] Save Preset      [L] Load Preset         [Q] Quit"
        print(self.format_line_exact(action2_content, ""))
    
    def print_status_section(self):
        """Print validation status and warnings"""
        is_valid, errors = self.config.is_valid()
        
        # Empty line
        print(self.format_line_exact("", ""))
        
        if errors:
            # Issues header
            header_content = "! ISSUES TO FIX:"
            colored_header = f"{Fore.RED}{Style.BRIGHT}{header_content}{Style.RESET_ALL}"
            print(self.format_line_exact(header_content, "", colored_header))
            
            # Show errors
            for error in errors[:3]:  # Show max 3 errors
                error_content = f"  • {error}"
                colored_error = f"  {Fore.RED}• {error}{Style.RESET_ALL}"
                print(self.format_line_exact(error_content, "", colored_error))
        else:
            success_content = "OK Configuration ready - all settings validated"
            colored_success = f"{Fore.GREEN}{success_content}{Style.RESET_ALL}"
            print(self.format_line_exact(success_content, "", colored_success))
    
    def print_separator(self):
        """Print a separator line"""
        # Ensure separator line matches content format exactly
        separator_content = self.sep_line * self.content_width
        print(f"{self.v_line} {separator_content} {self.v_line}")
    
    def display_dashboard(self):
        """Display the complete dashboard"""
        self.clear_screen()
        self.print_header()
        self.print_files_section()
        self.print_separator()
        self.print_config_section()
        self.print_separator()
        self.print_actions_section()
        self.print_separator()
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
        "anthonyDRL300k_2.csv",
        "hollemanDRL200k_3.csv"
    ]
    dashboard.config.filtering.enabled = True
    
    print("Testing improved dashboard alignment...")
    dashboard.display_dashboard()
    print(f"\n{Fore.GREEN}Dashboard alignment test completed!{Style.RESET_ALL}")
    print("Check if all the right borders (║) are properly aligned.")


if __name__ == "__main__":
    test_dashboard()