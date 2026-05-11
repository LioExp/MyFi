from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

from rich.table import Table

from myfi.core.base_chunk import BaseChunk
from myfi.chunks.extras.geo.geoip_plugin import GeoIPPlugin
from myfi.core.config_manager import ConfigManager
from myfi.ui.cli.theme import make_console

logger = logging.getLogger(__name__)

_BOGUS_PREFIXES = (
    "0.", "127.", "169.254.", "192.168.",
    "10.", "172.16.", "224.", "239.", "255.",
)


# CHUNK
class GeoLocateChunk(BaseChunk):
    """Geolocates external IPs contacted by the network."""

    def __init__(self, config: Any = None):
        super().__init__(config)
        self.config    = config or ConfigManager()
        self.interface = self.config.get("interface", "wlan0")
        self.geoip     = GeoIPPlugin()

    @staticmethod
    def manifest() -> dict:
        return {
            "name":        "GeoLocate",
            "version":     "1.0.0",
            "description": "Geolocates external IPs contacted by the network.",
            "inputs":      {},
            "outputs":     {"connections": {"type": "list"}},
            "permissions": ["network:capture", "network:outbound"],
            "cli_commands": ["geo show", "geo show --ip"],
        }

    def _capture_ips(self, duration: int = 15) -> list[str]:
        cmd = [
            "tshark", "-i", self.interface,
            "-a", f"duration:{duration}",
            "-T", "fields", "-e", "ip.dst",
            "-Y", "ip.dst",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 10,
            )
            if result.returncode != 0:
                logger.warning(
                    f"tshark exited with code {result.returncode}: "
                    f"{result.stderr.strip()[:120]}"
                )
            ips: set[str] = set()
            for line in result.stdout.splitlines():
                ip = line.strip()
                if ip and not ip.startswith(_BOGUS_PREFIXES):
                    ips.add(ip)
            return list(ips)
        except FileNotFoundError:
            logger.error("tshark not found. Install with: apt install tshark")
            return []
        except subprocess.TimeoutExpired:
            logger.error(f"tshark: timeout after {duration + 10}s.")
            return []
        except Exception as e:
            logger.error(f"_capture_ips: unexpected error: {e}")
            return []

    def run(self, input_data: dict = None) -> dict:
        duration = int((input_data or {}).get("duration", 15))

        try:
            ips = self._capture_ips(duration=duration)
        except Exception as e:
            logger.exception(f"GeoLocate.run: capture failed: {e}")
            return {"connections": [], "error": str(e)}

        if not ips:
            return {"connections": [], "message": "No external traffic captured."}

        connections = []
        for ip in ips:
            try:
                geo = self.geoip.lookup(ip)
                connections.append(geo or {
                    "ip":      ip,
                    "country": "unknown",
                    "city":    "unknown",
                    "isp":     "unknown",
                    "maps_url": "#",
                })
            except Exception as e:
                logger.warning(f"GeoLocate.run: lookup failed for {ip}: {e}")
                connections.append({
                    "ip":      ip,
                    "country": "unknown",
                    "city":    "unknown",
                    "isp":     "lookup error",
                    "maps_url": "#",
                })

        return {"connections": connections}


# REGISTRATION
def register_chunk(engine, subparsers) -> None:
    chunk = GeoLocateChunk(ConfigManager())
    engine.register(chunk)

    geo_parser = subparsers.add_parser("geo", help="IP geolocation")
    geo_sub    = geo_parser.add_subparsers(dest="geo_command")
    geo_show   = geo_sub.add_parser("show", help="Show geolocated IPs")
    geo_show.add_argument("--ip", type=str, help="Specific IP (manual mode)")

    # chunk injected — no re-instantiation in the callback
    engine.register_cli_handler("geo", _make_geo_callback(chunk))

# CALLBACK FACTORY
def _make_geo_callback(chunk: GeoLocateChunk):
    """Captures the chunk already registered in the engine — zero re-instantiations."""

    def _callback(args) -> None:
        console = make_console()

        if getattr(args, "ip", None):
            _show_single(console, chunk, args.ip)
        else:
            _show_capture(console, chunk)

    return _callback


# DISPLAY MODES
def _show_single(console, chunk: GeoLocateChunk, ip: str) -> None:
    """Geolocates a specific IP — reuses the chunk's plugin."""
    console.print(
        f"\n[myfi.dim]── GEOLOCATE ENGINE {'─' * 20} [ manual lookup ][/myfi.dim]"
    )

    with console.status(
        f"[myfi.cyan]Geolocating {ip}...[/myfi.cyan]", spinner="dots"
    ):
        try:
            data = chunk.geoip.lookup(ip)
        except Exception as e:
            console.print(f"[myfi.red][ FAIL ] Lookup error: {e}[/myfi.red]")
            return

    if data is None:
        console.print(
            f"[myfi.red][ FAIL ] Could not geolocate {ip}.[/myfi.red]"
        )
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="myfi.dim",  width=16)
    table.add_column(style="myfi.body")

    for label, value in [
        ("ip",          data.get("ip",        "--")),
        ("country",     data.get("country",   "unknown")),
        ("city",        data.get("city",      "unknown")),
        ("latitude",    str(data.get("latitude",  "--"))),
        ("longitude",   str(data.get("longitude", "--"))),
        ("isp",         data.get("isp",       "unknown")),
        ("organization", data.get("org",       "unknown")),
    ]:
        table.add_row(label, f"[myfi.body]{value}[/myfi.body]")

    maps = data.get("maps_url", "#")
    if maps and maps != "#":
        table.add_row("map", f"[myfi.blue][link={maps}]{maps}[/link][/myfi.blue]")

    console.print(table)
    console.print()


def _show_capture(console, chunk: GeoLocateChunk) -> None:
    """Captures traffic and geolocates external IPs."""
    console.print(
        f"\n[myfi.dim]── GEOLOCATE ENGINE {'─' * 20} [ live capture ][/myfi.dim]"
    )

    start_time = time.time()

    with console.status(
        "[myfi.cyan]Capturing external traffic...[/myfi.cyan]", spinner="dots"
    ):
        result = chunk.run()

    elapsed     = time.time() - start_time
    connections = result.get("connections", [])

    # capture error
    if error := result.get("error"):
        console.print(f"[myfi.red][ FAIL ] {error}[/myfi.red]")
        return

    if not connections:
        console.print(
            "[myfi.amber][ WARN ] No external traffic found.[/myfi.amber]\n"
            "[myfi.dim]         Run 'myfi monitor start --live' first.[/myfi.dim]"
        )
        return

    console.print(f"[myfi.dim]{'─' * 70}[/myfi.dim]")

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("IP",      style="myfi.blue", width=18)
    table.add_column("COUNTRY", style="myfi.body", width=22)
    table.add_column("CITY",    style="myfi.body", width=18)
    table.add_column("ISP",     style="myfi.dim",  width=28)

    for conn in connections:
        table.add_row(
            f"[myfi.blue]{conn.get('ip',      '--')}[/myfi.blue]",
            f"[myfi.body]{conn.get('country', 'unknown')}[/myfi.body]",
            f"[myfi.body]{conn.get('city',    'unknown')}[/myfi.body]",
            f"[myfi.dim]{conn.get('isp',      'unknown')}[/myfi.dim]",
        )

    console.print(table)
    console.print(f"[myfi.dim]{'─' * 70}[/myfi.dim]")

    n_countries = len({
        c.get("country") for c in connections
        if c.get("country") not in ("unknown", None)
    })
    n_isps = len({
        c.get("isp") for c in connections
        if c.get("isp") not in ("unknown", "lookup error", None)
    })

    console.print(
        f"[myfi.dim]targets: [/myfi.dim][myfi.cyan]{len(connections)}[/myfi.cyan]"
        f"[myfi.dim]  ·  countries: [/myfi.dim][myfi.cyan]{n_countries}[/myfi.cyan]"
        f"[myfi.dim]  ·  ISPs: [/myfi.dim][myfi.cyan]{n_isps}[/myfi.cyan]"
        f"[myfi.dim]  ·  time: {elapsed:.1f}s[/myfi.dim]"
    )
    console.print()
