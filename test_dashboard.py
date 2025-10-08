#!/usr/bin/env python3
"""
Test script for the dashboard integration
"""

import sys
import os

# Add the current directory to path
sys.path.append(os.getcwd())

try:
    from utils.dashboard_integration import DashboardController
    
    print("✅ Dashboard integration imports successfully!")
    
    controller = DashboardController()
    print("✅ Dashboard controller created successfully!")
    
    # Test CSV file scanning
    csv_files = controller.get_csv_files()
    print(f"✅ Found {len(csv_files)} CSV files in current directory")
    
    for i, file in enumerate(csv_files[:3], 1):  # Show first 3
        filename = os.path.basename(file)
        file_size = os.path.getsize(file) / (1024 * 1024)
        print(f"  {i}. {filename} ({file_size:.1f} MB)")
    
    if len(csv_files) > 3:
        print(f"  ... and {len(csv_files) - 3} more files")
    
    print("\n✅ Dashboard system is ready!")
    print("Run 'python generate_channel_report.py' to use the dashboard interface")
    print("Run 'python generate_channel_report.py --legacy' to use the old interface")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")