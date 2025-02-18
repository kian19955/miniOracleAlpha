from enum import Enum

class EventType(Enum):
    EVENT_TYPE = 'e'          # Event type
    EVENT_TIME = 'E'          # Event time
    SYMBOL = 's'              # Symbol
    CLIENT_ORDER_ID = 'c'     # Client order ID
    SIDE = 'S'                # Side (BUY/SELL)
    ORDER_TYPE = 'o'          # Order type (LIMIT/MARKET)
    TIME_IN_FORCE = 'f'       # Time in force
    ORDER_QUANTITY = 'q'      # Order quantity
    ORDER_PRICE = 'p'         # Order price
    STOP_PRICE = 'P'          # Stop price
    ICEBERG_QUANTITY = 'F'    # Iceberg quantity
    ORDER_LIST_ID = 'g'       # OrderListId
    ORIGINAL_CLIENT_ORDER_ID = 'C'  # Original client order ID (for canceled orders)
    CURRENT_EXECUTION_TYPE = 'x'    # Current execution type
    CURRENT_ORDER_STATUS = 'X'      # Current order status
    ORDER_REJECT_REASON = 'r'       # Order reject reason
    ORDER_ID = 'i'            # Order ID
    LAST_FILLED_TRADE_QUANTITY = 'l'  # Last filled trade quantity
    ACCUMULATED_FILLED_QUANTITY = 'z'  # Accumulated filled quantity
    LAST_FILLED_TRADE_PRICE = 'L'    # Last filled trade price
    COMMISSION_AMOUNT = 'n'   # Commission amount
    COMMISSION_ASSET = 'N'    # Commission asset
    TRANSACTION_TIME = 'T'    # Transaction time
    TRADE_ID = 't'            # Trade ID
    IGNORE = 'I'              # Ignore
    IS_MAKER_SIDE = 'm'       # Is the buyer the market maker?
    ORDER_CREATION_TIME = 'O' # Order creation time
    QUOTE_ASSET_TRADED = 'Z'  # Quote asset traded
    LAST_QUOTE_ASSET_TRADED = 'Y'  # Last quote asset traded

    @classmethod
    def from_code(cls, code):
        """Retrieve the EventType by its code."""
        return cls[code] if code in cls.__members__ else None