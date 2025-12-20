"""
Main TUI Controller for OBD2 Simulator visualization.

Provides real-time terminal UI with transaction log, stats, and ECU status.
"""

import threading
import time
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .transaction_log import TransactionLog, Transaction, TransactionType
from .panels import (
    HeaderPanel,
    StatsPanel,
    ECUStatusPanel,
    ServiceBreakdownPanel,
    LiveIndicator,
)
from .decoder import OBD2Decoder

if TYPE_CHECKING:
    from ..profile import ECUConfig


class SimulatorTUI:
    """
    Terminal User Interface for OBD2 Simulator.

    Provides real-time visualization of:
    - Transaction log with auto-scrolling
    - Statistics (requests, responses, broadcasts)
    - ECU status indicators
    - Service breakdown
    """

    def __init__(
        self,
        profile_name: str = "",
        vin: str = "",
        interface: str = "",
        max_transactions: int = 20,
        refresh_rate: float = 4.0,
    ):
        """
        Initialize the TUI.

        Args:
            profile_name: Name of the loaded vehicle profile
            vin: Vehicle VIN
            interface: CAN interface name
            max_transactions: Maximum transactions to display
            refresh_rate: Screen refresh rate in Hz
        """
        self.console = Console()
        self.refresh_rate = refresh_rate

        # Components
        self.header = HeaderPanel(profile_name, vin, interface)
        self.transaction_log = TransactionLog(max_entries=max_transactions)
        self.stats = StatsPanel()
        self.ecu_status = ECUStatusPanel()
        self.service_breakdown = ServiceBreakdownPanel()
        self.live_indicator = LiveIndicator()

        # State
        self._running = False
        self._live: Optional[Live] = None
        self._lock = threading.Lock()

    def register_ecu(self, ecu_id: int, name: str) -> None:
        """Register an ECU for status tracking."""
        self.ecu_status.register_ecu(ecu_id, name)
        self.header.ecu_count = len(self.ecu_status.ecus)

    def register_ecus(self, ecus: List['ECUConfig']) -> None:
        """Register multiple ECUs from config."""
        for ecu in ecus:
            self.register_ecu(ecu.response_id, ecu.name)

    def record_request(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """
        Record an incoming OBD2 request.

        Args:
            can_id: CAN arbitration ID
            data: CAN data bytes
            extended: Whether extended frame
        """
        with self._lock:
            self.transaction_log.add_request(can_id, data, extended)
            self.stats.record_request()
            self.live_indicator.pulse()

            # Record service for breakdown
            if len(data) >= 2:
                service = data[1]
                self.service_breakdown.record_service(service)

    def record_response(
        self,
        can_id: int,
        data: bytes,
        ecu_name: Optional[str] = None,
        extended: bool = False
    ) -> None:
        """
        Record an outgoing OBD2 response.

        Args:
            can_id: CAN arbitration ID (ECU response ID)
            data: CAN data bytes
            ecu_name: Optional ECU name
            extended: Whether extended frame
        """
        with self._lock:
            self.transaction_log.add_response(can_id, data, ecu_name, extended)
            self.stats.record_response()
            self.ecu_status.record_response(can_id)
            self.live_indicator.pulse()

    def record_broadcast(self, can_id: int, data: bytes, extended: bool = False) -> None:
        """
        Record a broadcast message.

        Args:
            can_id: CAN arbitration ID
            data: CAN data bytes
            extended: Whether extended frame
        """
        with self._lock:
            self.transaction_log.add_broadcast(can_id, data, extended)
            self.stats.record_broadcast()

    def record_error(self, can_id: int, data: bytes, message: str = "") -> None:
        """
        Record an error transaction.

        Args:
            can_id: CAN arbitration ID
            data: CAN data bytes
            message: Error message
        """
        with self._lock:
            self.transaction_log.add_error(can_id, data, message)
            self.stats.record_error()

    def _build_layout(self) -> Layout:
        """Build the screen layout."""
        layout = Layout()

        # Main vertical layout
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=10),
        )

        # Main area: transaction log
        layout["main"].update(self.transaction_log.render())

        # Footer: stats panels side by side
        layout["footer"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="ecu", ratio=1),
            Layout(name="services", ratio=2),
        )

        layout["footer"]["stats"].update(self.stats.render())
        layout["footer"]["ecu"].update(self.ecu_status.render())
        layout["footer"]["services"].update(self.service_breakdown.render())

        # Header
        layout["header"].update(self.header.render())

        return layout

    def _render(self) -> Layout:
        """Render the full TUI."""
        with self._lock:
            return self._build_layout()

    def start(self) -> None:
        """Start the TUI display loop."""
        self._running = True
        self.header.set_running(True)

        with Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_rate,
            screen=True,
        ) as live:
            self._live = live
            while self._running:
                live.update(self._render())
                time.sleep(1.0 / self.refresh_rate)

    def start_async(self) -> threading.Thread:
        """
        Start the TUI in a background thread.

        Returns:
            The background thread running the TUI
        """
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        """Stop the TUI display loop."""
        self._running = False
        self.header.set_running(False)

    def print_summary(self) -> None:
        """Print a summary after TUI stops."""
        self.console.print()
        self.console.print("[bold]Session Summary[/bold]")
        self.console.print(f"  Total Requests:   {self.stats.requests:,}")
        self.console.print(f"  Total Responses:  {self.stats.responses:,}")
        self.console.print(f"  Total Broadcasts: {self.stats.broadcasts:,}")
        self.console.print(f"  Total Errors:     {self.stats.errors}")
        self.console.print()


def create_tui_for_simulator(simulator) -> SimulatorTUI:
    """
    Create a TUI instance configured for a simulator.

    Args:
        simulator: OBD2Simulator instance

    Returns:
        Configured SimulatorTUI
    """
    tui = SimulatorTUI(
        profile_name=simulator.profile.name,
        vin=simulator.profile.get_vin(),
        interface=simulator.config.can_interface,
    )

    # Register ECUs
    tui.register_ecus(simulator.profile.get_ecus())

    return tui
