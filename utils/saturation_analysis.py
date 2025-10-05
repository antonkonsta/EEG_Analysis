"""
Saturation analysis utilities for EEG data processing.

This module contains functions for detecting and analyzing channel saturation.
"""

import numpy as np


def count_saturated_channels_any_point(df, channels, low_thresh=0.053, high_thresh=3.247):
    """
    Counts channels that experience saturation at ANY point in time,
    i.e., have any data points below low_thresh or above high_thresh.

    Returns:
        num_saturated: int, number of channels experiencing saturation
        below_saturated: list of channel names with points below low_thresh
        above_saturated: list of channel names with points above high_thresh
    """
    below_saturated = []
    above_saturated = []
    for ch in channels:
        if ch in df.columns:
            data = df[ch]
            # Check if ANY point crosses the thresholds
            if (data < low_thresh).any():
                below_saturated.append(ch)
            if (data > high_thresh).any():
                above_saturated.append(ch)
    num_saturated = len(set(below_saturated + above_saturated))
    return num_saturated, below_saturated, above_saturated