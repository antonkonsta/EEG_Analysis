# EEG Channel Analysis Tool

A Python tool for analyzing EEG data quality and generating comprehensive PDF reports.

## Requirements

- Python 3.7+
- Required packages (see requirements.txt)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

**Before running:** Place your CSV data files in the main project folder (same level as the Python script).

```bash
python generate_channel_report.py
```

The script will guide you through:
1. **File selection** - Choose your CSV file
2. **Channel mapping** - Select electrode layout
3. **Output folder** - Where to save the report
4. **Analysis settings** - Configure thresholds and filtering
5. **Output filename** - Name your report

## Input Format

CSV files with EEG data where:
- Each column is a channel
- Rows are time samples
- Optional: Column names like "Channel 1", "Channel 2", etc.

## Output

PDF report with:
- Signal quality analysis
- Amplitude and saturation detection
- Frequency domain analysis
- Individual channel plots
- Quality summary

## Settings

Your preferences (thresholds, filters) are automatically saved for next use.

## Channel Mappings

Place custom electrode mapping files in `channel_mappings/` folder as CSV files.