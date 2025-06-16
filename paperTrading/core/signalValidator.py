from typing import Optional
from paperTrading.enums import Side


class SignalValidator:
    """
    Validates incoming signal sides against a confirmation-streak threshold
    and optional block-reentry-until-signal-change logic.
    """
    def __init__(
        self,
        streak_threshold: int = 1,
        block_reentry_until_signal_change: bool = False,
    ):
        if streak_threshold < 1:
            raise ValueError("streak_threshold must be at least 1")

        self.streak_threshold = streak_threshold
        self.block_reentry = block_reentry_until_signal_change

        self._last_signal: Optional[Side] = None
        self._streak: int = 0
        self._last_executed: Optional[Side] = None

    def reset_on_neutral(self) -> None:
        """Call when a neutral/none signal arrives to break the chain."""
        self._last_signal = None

    def allow(self, side: Side) -> bool:
        """
        Return True if an order on `side` should be executed now,
        based on streak threshold and re-entry guard.
        """
        # update streak
        if self._last_signal == side:
            self._streak += 1
        else:
            self._streak = 1
        self._last_signal = side

        # block until we have at least the threshold
        if self._streak < self.streak_threshold:
            return False

        # optional block-reentry check
        if self.block_reentry and self._last_executed == side:
            return False

        # passed all checks: record execution and allow
        self._last_executed = side
        return True