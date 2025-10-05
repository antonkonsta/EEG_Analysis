"""
Channel mapping utilities for EEG data processing.

This module contains minimal utilities needed for channel mapping operations
in the EEG analysis pipeline.
"""

import os
import pandas as pd


def apply_channel_mapping(df, channel_map):
    """
    Applies a channel mapping dictionary to rename DataFrame columns from 
    CSV channel names to anatomical EEG electrode names.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the EEG data.
        channel_map (dict): A dictionary mapping current column names to new names.
                           e.g., {"Channel 1": "Fp1", "Channel 2": "Fp2", ...}

    Returns:
        pd.DataFrame: The DataFrame with renamed columns.

    Raises:
        ValueError: If any keys in channel_map are not found in the DataFrame columns.
    """
    # Check if all keys in channel_map exist in the DataFrame
    missing_channels = [channel for channel in channel_map.keys() if channel not in df.columns]
    if missing_channels:
        raise ValueError(f"The following channels were not found in the DataFrame: {missing_channels}. "
                         f"Available channels: {list(df.columns)}")

    # Create a copy of the DataFrame to avoid modifying the original
    df_mapped = df.copy()
    
    # Rename the columns according to the mapping
    df_mapped = df_mapped.rename(columns=channel_map)
    
    return df_mapped


def load_channel_map(file_path):
    """
    Loads a channel mapping from a CSV file. The CSV should have two columns:
    'csv_name' (original column names) and 'electrode_name' (anatomical names).

    Parameters:
        file_path (str): Path to the CSV file containing the channel mapping.

    Returns:
        dict: A dictionary mapping CSV column names to electrode names.

    Raises:
        FileNotFoundError: If the mapping file is not found.
        ValueError: If the CSV doesn't have the required columns.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Channel mapping file '{file_path}' not found.")
    
    mapping_df = pd.read_csv(file_path)
    
    # Check if required columns exist
    required_columns = ['csv_name', 'electrode_name']
    missing_columns = [col for col in required_columns if col not in mapping_df.columns]
    if missing_columns:
        raise ValueError(f"Channel mapping CSV must contain columns: {required_columns}. "
                         f"Missing: {missing_columns}")
    
    # Convert to dictionary
    channel_map = dict(zip(mapping_df['csv_name'], mapping_df['electrode_name']))
    
    return channel_map