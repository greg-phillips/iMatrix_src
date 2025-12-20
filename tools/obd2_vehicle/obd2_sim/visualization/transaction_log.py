"""
Transaction Log for OBD2 Simulator visualization.

Maintains a scrolling window of recent transactions with timestamps.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Deque, Optional, List

from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.style import Style

from .decoder import OBD2Decoder


class TransactionType(Enum):
    """Type of CAN transaction."""
    REQUEST = "request"       # Incoming OBD2 request
    RESPONSE = "response"     # Outgoing OBD2 response
    BROADCAST = "broadcast"   # Periodic broadcast message
    FLOW_CTRL = "flow_ctrl"   # ISO-TP flow control
    ERROR = "error"           # Error/negative response


@dataclass
class Transaction:
    """Single CAN transaction record."""
    timestamp: datetime
    tx_type: TransactionType
    can_id: int
    data: bytes
    ecu_name: Optional[str] = None
    decoded: str = ""
    is_extended: bool = False

    def __post_init__(self):
        """Decode the transaction if not already decoded."""
        if not self.decoded:
            self.decoded = self._auto_decode()

    def _auto_decode(self) -> str:
        """Auto-decode based on transaction type."""
        if self.tx_type == TransactionType.REQUEST:
            return OBD2Decoder.format_request_short(self.data)
        elif self.tx_type == TransactionType.RESPONSE:
            return OBD2Decoder.format_response_short(self.data)
        elif self.tx_type == TransactionType.BROADCAST:
            return OBD2Decoder.format_broadcast_short(self.can_id, self.data)
        elif self.tx_type == TransactionType.FLOW_CTRL:
            return "Flow Control"
        elif self.tx_type == TransactionType.ERROR:
            return "Error"
        return ""


# Color styles for different transaction types and ECUs
STYLES = {
    TransactionType.REQUEST: Style(color="cyan", bold=True),
    TransactionType.RESPONSE: Style(color="green"),
    TransactionType.BROADCAST: Style(color="yellow"),
    TransactionType.FLOW_CTRL: Style(color="blue", dim=True),
    TransactionType.ERROR: Style(color="red", bold=True),
}

ECU_STYLES = {
    0x7E8: Style(color="bright_green"),
    0x7E9: Style(color="bright_blue"),
    0x7EA: Style(color="bright_cyan"),
    0x7EB: Style(color="bright_magenta"),
    0x7EC: Style(color="bright_yellow"),
    0x7ED: Style(color="bright_white"),
    0x7EE: Style(color="green"),
    0x7EF: Style(color="magenta"),
}

DIRECTION_SYMBOLS = {
    TransactionType.REQUEST: "◀RX",
    TransactionType.RESPONSE: "▶TX",
    TransactionType.BROADCAST: "📡 ",
    TransactionType.FLOW_CTRL: "↔FC",
    TransactionType.ERROR: "⚠ER",
}


class TransactionLog:
    """
    Thread-safe transaction log with fixed-size scrolling window.

    Maintains the last N transactions and provides rich rendering.
    """

    def __init__(self, max_entries: int = 20):
        """
        Initialize transaction log.

        Args:
            max_entries: Maximum number of transactions to keep
        """
        self.max_entries = max_entries
        self._transactions: Deque[Transaction] = deque(maxlen=max_entries)
        self._lock = Lock()
        self._total_count = 0

    def add(self, transaction: Transaction) -> None:
        """
        Add a transaction to the log.

        Args:
            transaction: Transaction to add
        """
        with self._lock:
            self._transactions.append(transaction)
            self._total_count += 1

    def add_request(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """Add an incoming request transaction."""
        self.add(Transaction(
            timestamp=datetime.now(),
            tx_type=TransactionType.REQUEST,
            can_id=can_id,
            data=data,
            is_extended=extended,
        ))

    def add_response(self, can_id: int, data: bytes, ecu_name: Optional[str] = None,
                     extended: bool = False) -> None:
        """Add an outgoing response transaction."""
        self.add(Transaction(
            timestamp=datetime.now(),
            tx_type=TransactionType.RESPONSE,
            can_id=can_id,
            data=data,
            ecu_name=ecu_name,
            is_extended=extended,
        ))

    def add_broadcast(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """Add a broadcast message transaction."""
        self.add(Transaction(
            timestamp=datetime.now(),
            tx_type=TransactionType.BROADCAST,
            can_id=can_id,
            data=data,
            is_extended=extended,
        ))

    def add_error(self, can_id: int, data: bytes, message: str = "") -> None:
        """Add an error transaction."""
        self.add(Transaction(
            timestamp=datetime.now(),
            tx_type=TransactionType.ERROR,
            can_id=can_id,
            data=data,
            decoded=message or "Error",
        ))

    def get_transactions(self) -> List[Transaction]:
        """Get a copy of current transactions."""
        with self._lock:
            return list(self._transactions)

    def clear(self) -> None:
        """Clear all transactions."""
        with self._lock:
            self._transactions.clear()

    @property
    def total_count(self) -> int:
        """Total number of transactions since start."""
        return self._total_count

    def render(self) -> Panel:
        """
        Render the transaction log as a rich Panel.

        Returns:
            Rich Panel containing the transaction table
        """
        table = Table(
            show_header=True,
            header_style="bold white",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("TIME", style="dim", width=10, no_wrap=True)
        table.add_column("DIR", width=4, no_wrap=True)
        table.add_column("CAN ID", width=8, no_wrap=True)
        table.add_column("DATA", width=26, no_wrap=True)
        table.add_column("DECODED", no_wrap=False)

        with self._lock:
            transactions = list(self._transactions)

        for tx in transactions:
            # Time
            time_str = tx.timestamp.strftime("%H:%M:%S")

            # Direction with symbol and color
            dir_symbol = DIRECTION_SYMBOLS.get(tx.tx_type, "???")
            dir_text = Text(dir_symbol, style=STYLES.get(tx.tx_type))

            # CAN ID with ECU coloring for responses
            if tx.is_extended:
                id_str = f"0x{tx.can_id:08X}"
            else:
                id_str = f"0x{tx.can_id:03X}"

            if tx.tx_type == TransactionType.RESPONSE and tx.can_id in ECU_STYLES:
                id_text = Text(id_str, style=ECU_STYLES[tx.can_id])
            else:
                id_text = Text(id_str, style=STYLES.get(tx.tx_type))

            # Data bytes
            data_str = " ".join(f"{b:02X}" for b in tx.data[:8])
            data_text = Text(data_str, style="dim white")

            # Decoded message
            decoded_text = Text(tx.decoded, style=STYLES.get(tx.tx_type))

            table.add_row(time_str, dir_text, id_text, data_text, decoded_text)

        # Fill empty rows if needed
        empty_rows = self.max_entries - len(transactions)
        for _ in range(empty_rows):
            table.add_row("", "", "", "", "")

        title = f"Transaction Log (Last {self.max_entries})"
        if self._total_count > self.max_entries:
            title += f" - Total: {self._total_count:,}"

        return Panel(
            table,
            title=title,
            title_align="left",
            border_style="blue",
        )

    def render_compact(self, height: int = 10) -> Panel:
        """
        Render a compact version of the transaction log.

        Args:
            height: Number of rows to show

        Returns:
            Rich Panel with compact transaction list
        """
        lines = []

        with self._lock:
            transactions = list(self._transactions)[-height:]

        for tx in transactions:
            time_str = tx.timestamp.strftime("%H:%M:%S")
            dir_symbol = DIRECTION_SYMBOLS.get(tx.tx_type, "?")

            if tx.is_extended:
                id_str = f"0x{tx.can_id:08X}"
            else:
                id_str = f"0x{tx.can_id:03X}"

            line = Text()
            line.append(f"{time_str} ", style="dim")
            line.append(f"{dir_symbol} ", style=STYLES.get(tx.tx_type))

            if tx.tx_type == TransactionType.RESPONSE and tx.can_id in ECU_STYLES:
                line.append(f"{id_str} ", style=ECU_STYLES[tx.can_id])
            else:
                line.append(f"{id_str} ", style=STYLES.get(tx.tx_type))

            line.append(tx.decoded, style=STYLES.get(tx.tx_type))
            lines.append(line)

        # Pad with empty lines
        while len(lines) < height:
            lines.insert(0, Text(""))

        content = Text("\n").join(lines)

        return Panel(
            content,
            title="Transactions",
            title_align="left",
            border_style="blue",
        )
