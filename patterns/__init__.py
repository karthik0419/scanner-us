"""
Pattern detection modules for scanner-us.

Each detector returns a dict with keys:
    pattern, status, entry, stop_loss, target_1, target_2,
    risk_pct, rr, cmp, mtf_confirmed

Or None if no pattern found.
"""

from .flags import detect_bull_flag, detect_pennant
from .triangle import detect_ascending_triangle, detect_symmetrical_triangle
from .wedge import detect_falling_wedge
from .channel import detect_channel_breakout, detect_rectangle
from .double_top import detect_double_top
from .head_shoulders import detect_inverse_head_shoulders

__all__ = [
    'detect_bull_flag',
    'detect_pennant',
    'detect_ascending_triangle',
    'detect_symmetrical_triangle',
    'detect_falling_wedge',
    'detect_channel_breakout',
    'detect_rectangle',
    'detect_double_top',
    'detect_inverse_head_shoulders',
]
