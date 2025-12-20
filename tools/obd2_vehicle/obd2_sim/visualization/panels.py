"""
UI Panel components for OBD2 Simulator visualization.

Provides stats panels, ECU status, and service breakdown displays.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich.layout import Layout
from rich.style import Style
from rich.columns import Columns


# ECU color mapping
ECU_COLORS = {
    0x7E8: "bright_green",
    0x7E9: "bright_blue",
    0x7EA: "bright_cyan",
    0x7EB: "bright_magenta",
    0x7EC: "bright_yellow",
    0x7ED: "bright_white",
    0x7EE: "green",
    0x7EF: "magenta",
}


class HeaderPanel:
    """Header panel showing simulator status and basic info."""

    def __init__(self, profile_name: str = "", vin: str = "", interface: str = ""):
        self.profile_name = profile_name
        self.vin = vin
        self.interface = interface
        self.start_time: Optional[datetime] = None
        self.status = "Stopped"
        self.ecu_count = 0

    def set_running(self, running: bool = True) -> None:
        """Set running status."""
        self.status = "Running" if running else "Stopped"
        if running and self.start_time is None:
            self.start_time = datetime.now()

    def render(self) -> Panel:
        """Render the header panel."""
        # Calculate uptime
        if self.start_time:
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_str = "--:--:--"

        # Status indicator
        if self.status == "Running":
            status_text = Text("●", style="bold green")
            status_text.append(f" {self.status}", style="green")
        else:
            status_text = Text("○", style="bold red")
            status_text.append(f" {self.status}", style="red")

        # Build info line
        info_parts = [
            f"Interface: [cyan]{self.interface}[/cyan]",
            f"VIN: [yellow]{self.vin}[/yellow]",
            f"ECUs: [green]{self.ecu_count}[/green]",
            f"Uptime: [blue]{uptime_str}[/blue]",
        ]
        info_line = "    ".join(info_parts)

        # Title with status
        title_text = Text()
        title_text.append(f"OBD2 Vehicle Simulator - {self.profile_name}  ", style="bold white")

        content = Text.from_markup(info_line)

        return Panel(
            content,
            title=title_text,
            title_align="left",
            subtitle=status_text,
            subtitle_align="right",
            border_style="bright_blue",
        )


class StatsPanel:
    """Statistics panel showing request/response counts."""

    def __init__(self):
        self.requests = 0
        self.responses = 0
        self.broadcasts = 0
        self.errors = 0
        self.start_time: Optional[datetime] = None
        self._request_times: List[datetime] = []

    def record_request(self) -> None:
        """Record a request."""
        self.requests += 1
        now = datetime.now()
        self._request_times.append(now)
        # Keep only last 60 seconds
        cutoff = now - timedelta(seconds=60)
        self._request_times = [t for t in self._request_times if t > cutoff]

    def record_response(self) -> None:
        """Record a response."""
        self.responses += 1

    def record_broadcast(self) -> None:
        """Record a broadcast."""
        self.broadcasts += 1

    def record_error(self) -> None:
        """Record an error."""
        self.errors += 1

    @property
    def requests_per_second(self) -> float:
        """Calculate requests per second over last 60s."""
        if not self._request_times:
            return 0.0
        now = datetime.now()
        cutoff = now - timedelta(seconds=60)
        recent = [t for t in self._request_times if t > cutoff]
        if len(recent) < 2:
            return 0.0
        time_span = (recent[-1] - recent[0]).total_seconds()
        if time_span <= 0:
            return 0.0
        return len(recent) / time_span

    def render(self) -> Panel:
        """Render the stats panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Requests:", f"[cyan]{self.requests:,}[/cyan]")
        table.add_row("Responses:", f"[green]{self.responses:,}[/green]")
        table.add_row("Broadcasts:", f"[yellow]{self.broadcasts:,}[/yellow]")
        table.add_row("Errors:", f"[red]{self.errors}[/red]")
        table.add_row("Req/sec:", f"[blue]{self.requests_per_second:.1f}[/blue]")

        return Panel(
            table,
            title="Statistics",
            title_align="left",
            border_style="green",
        )


class ECUStatusPanel:
    """Panel showing status of each ECU."""

    def __init__(self):
        self.ecus: Dict[int, Dict[str, Any]] = {}

    def register_ecu(self, ecu_id: int, name: str) -> None:
        """Register an ECU."""
        self.ecus[ecu_id] = {
            "name": name,
            "responses": 0,
            "active": True,
            "last_response": None,
        }

    def record_response(self, ecu_id: int) -> None:
        """Record a response from an ECU."""
        if ecu_id in self.ecus:
            self.ecus[ecu_id]["responses"] += 1
            self.ecus[ecu_id]["last_response"] = datetime.now()

    def render(self) -> Panel:
        """Render the ECU status panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("ECU", width=20)
        table.add_column("Status", width=3)
        table.add_column("Count", justify="right")

        for ecu_id, info in sorted(self.ecus.items()):
            color = ECU_COLORS.get(ecu_id, "white")

            # Check if recently active
            if info["last_response"]:
                age = (datetime.now() - info["last_response"]).total_seconds()
                status = "●" if age < 5 else "○"
                status_style = color if age < 5 else "dim"
            else:
                status = "○"
                status_style = "dim"

            ecu_text = Text()
            ecu_text.append(f"0x{ecu_id:03X} ", style=f"bold {color}")
            ecu_text.append(f"({info['name']})", style="dim")

            table.add_row(
                ecu_text,
                Text(status, style=status_style),
                f"[{color}]{info['responses']:,}[/{color}]"
            )

        return Panel(
            table,
            title="ECU Status",
            title_align="left",
            border_style="magenta",
        )


class ServiceBreakdownPanel:
    """Panel showing breakdown of requests by service."""

    SERVICE_NAMES = {
        0x01: "Service 01",
        0x02: "Service 02",
        0x03: "Service 03",
        0x04: "Service 04",
        0x07: "Service 07",
        0x09: "Service 09",
        0x0A: "Service 0A",
    }

    def __init__(self):
        self.service_counts: Dict[int, int] = {}

    def record_service(self, service: int) -> None:
        """Record a service request."""
        self.service_counts[service] = self.service_counts.get(service, 0) + 1

    def render(self) -> Panel:
        """Render the service breakdown panel."""
        total = sum(self.service_counts.values()) or 1

        lines = []
        for service, count in sorted(self.service_counts.items(),
                                      key=lambda x: x[1], reverse=True)[:6]:
            pct = count * 100 / total
            name = self.SERVICE_NAMES.get(service, f"Service {service:02X}")

            # Create bar
            bar_width = 40
            filled = int(pct * bar_width / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Color based on service
            colors = ["cyan", "green", "yellow", "blue", "magenta", "red"]
            color = colors[list(self.service_counts.keys()).index(service) % len(colors)]

            line = Text()
            line.append(f"{name:12} ", style="bold")
            line.append(bar, style=color)
            line.append(f" {count:>5} ({pct:>4.0f}%)", style="dim")
            lines.append(line)

        if not lines:
            lines.append(Text("No requests yet", style="dim"))

        content = Text("\n").join(lines)

        return Panel(
            content,
            title="Service Breakdown",
            title_align="left",
            border_style="yellow",
        )


class LiveIndicator:
    """Small live indicator that pulses to show activity."""

    def __init__(self):
        self.last_activity = datetime.now()
        self._pulse_state = 0

    def pulse(self) -> None:
        """Record activity."""
        self.last_activity = datetime.now()
        self._pulse_state = 3

    def render(self) -> Text:
        """Render the live indicator."""
        age = (datetime.now() - self.last_activity).total_seconds()

        if self._pulse_state > 0:
            self._pulse_state -= 1
            return Text("◉ LIVE", style="bold bright_green")
        elif age < 1:
            return Text("● LIVE", style="bold green")
        elif age < 5:
            return Text("● IDLE", style="yellow")
        else:
            return Text("○ IDLE", style="dim red")
