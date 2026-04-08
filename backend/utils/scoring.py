"""
SHIELD Scoring Utilities
────────────────────────
Helper functions used across routers.
"""

from datetime import datetime


def get_sim_swap_minutes(sim_swap_event) -> int:
    """
    Returns minutes elapsed since SIM swap was triggered.

    Args:
        sim_swap_event: SimSwapEvent ORM instance (or None)

    Returns:
        int — minutes since trigger, or 0 if None
    """
    if sim_swap_event is None:
        return 0
    delta = datetime.utcnow() - sim_swap_event.triggered_at
    return max(0, int(delta.total_seconds() / 60))
