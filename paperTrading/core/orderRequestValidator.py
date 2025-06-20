from typing import Optional
import logging
from paperTrading.enums import OrderType
from paperTrading.models import OrderRequest

logger = logging.getLogger(__name__)


class OrderRequestValidator:
    """
    Validates whether an OrderRequest can be created, based on:
      - confirmation streak threshold
      - optional block-reentry-until-signal-change
      - presence of stop-loss or quantity
    """

    def __init__(
            self,
            streak_threshold: int = 1,
            block_reentry_until_signal_change: bool = False,
            default_stop_loss: Optional[float] = None,
    ):
        if streak_threshold < 1:
            raise ValueError("streak_threshold must be at least 1")

        self.streak_threshold = streak_threshold
        self.block_reentry = block_reentry_until_signal_change
        self.default_stop_loss = default_stop_loss

        # internal state
        self._last_signal: Optional[OrderType] = None
        self._streak: int = 0
        self._last_executed_side: Optional[OrderType] = None

    def reset_on_neutral(self) -> None:
        """
        Call when a strategy returns no actionable OrderRequest,
        to break the existing confirmation streak.
        """
        self._last_signal = None
        # next valid signal will reset streak to 1

    def is_valid(self, order_request: OrderRequest) -> bool:
        """
        Returns True if the given OrderRequest meets all validation rules.
        """
        side = order_request.type

        # 1) Confirmation streak
        self._streak = (self._streak + 1) if self._last_signal == side else 1
        self._last_signal = side

        if self._streak < self.streak_threshold:
            return False

        # 2) Block re-entry until signal change
        if self.block_reentry and self._last_executed_side == side:
            return False

        # 3) Ensure we have either stop_loss or direct qty
        if (
                order_request.stop_loss is None
                and self.default_stop_loss is None
                and order_request.qty is None
        ):
            logger.warning(
                "OrderRequest missing stop_loss and qty; cannot validate size."
            )
            return False

        # passed all checks
        self._last_executed_side = side
        return True

    def __repr__(self):
        return (
            f"<OrderRequestValidator(streak_threshold={self.streak_threshold}, "
            f"block_reentry={self.block_reentry}, "
            f"streak={self._streak}, last_signal={self._last_signal}, "
            f"last_executed={self._last_executed_side})>"
        )
