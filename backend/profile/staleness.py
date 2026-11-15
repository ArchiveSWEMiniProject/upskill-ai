"""Telling M2 that a student's recommendations are out of date.

mark_stale(student_id) is M2's published operation (docs/CONTRACTS.md,
"Internal module interfaces"). M1 calls it whenever a target role changes
(REQ-F1-33). Until M2 provides it, the default does nothing; M2 (or a test)
replaces it with set_stale_hook().
"""

from collections.abc import Callable

StaleHook = Callable[[int], None]


def _nothing(student_id: int) -> None:
    return None


_hook: StaleHook = _nothing


def set_stale_hook(hook: StaleHook | None) -> None:
    """Install M2's mark_stale; None restores the do-nothing default."""
    global _hook
    _hook = hook or _nothing


def mark_stale(student_id: int) -> None:
    _hook(student_id)
