"""Eval-Hawthorne-Effect: monitoring-notice arms layered on an unmodified ImpossibleBench."""

from .notices import FLAG_EXIT, INSTRUCTIONS, NOTICE_ARMS
from .tasks import hawthorne_lcb

__all__ = ["FLAG_EXIT", "INSTRUCTIONS", "NOTICE_ARMS", "hawthorne_lcb"]
