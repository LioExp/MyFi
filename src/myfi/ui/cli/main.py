from __future__ import annotations

import json
import logging
import re
import shlex
import subprocess
import sys
import importlib
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any
from threading import Thread

import argparse
from rich.live import Live
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from myfi.core.config_manager import ConfigManager
from myfi.core.engine import ChunkEngine
from myfi.core.scanner import Scanner
from myfi.chunks.extras.telegram_notifier import TelegramNotifierChunk
from myfi.ui.cli.setup_wizard import SetupWizard
from myfi.ui.cli.theme import make_console

console = make_console()
logger  = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════

def _create_engine() -> ChunkEngine:
    config = ConfigManager()
    engine = ChunkEngine(config)
    if config.get("telegram_token") and config.get("telegram_chat_id"):
        try:
            engine.register(TelegramNotifierChunk(config))
        except Exception as e:
            logger.error(f"TelegramNotifierChunk: {e}")
    return engine


def discover_and_register_chunks(engine: ChunkEngine, subparsers: Any) -> None:
    chunks_dir = Path(__file__).resolve().parent.parent.parent / "chunks" / "extras"
    for item in sorted(chunks_dir.iterdir()):
        if item.is_dir() and (item / "__init__.py").exists():
            try:
                mod = importlib.import_module(f"myfi.chunks.extras.{item.name}")
                if hasattr(mod, "register_chunk"):
                    mod.register_chunk(engine, subparsers)
                    logger.info(f"Chunk '{item.name}' registado.")
            except Exception as e:
                # visivel na consola — nao apenas no ficheiro de log
                logger.error(f"Chunk '{item.name}': {e}")
                console.print(
                    f"[myfi.amber][ WARN ] Chunk '{item.name}' failed to load: "
                    f"{e}[/myfi.amber]"
                )


# ════════════════════════════════════════════════════════════════
# FORMATAÇÃO
# ════════════════════════════════════════════════════════════════

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def _fmt_bar(current: int, limit: int, width: int = 10) -> str:
    if limit <= 0:
        return "[myfi.dim][ N/A ][/myfi.dim]"
    ratio  = min(current / limit, 1.0)
    filled = int(width * ratio)
    bar    = "█" * filled + "░" * (width - filled)
    if ratio >= 1.0:
        return f"[bold myfi.red][{bar}][/bold myfi.red]"
    if ratio > 0.8:
        return f"[bold myfi.amber][{bar}][/bold myfi.amber]"
    return f"[bold myfi.green][{bar}][/bold myfi.green]"


def _get_ip(iface: str) -> str:
    try:
        r = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", iface],
            capture_output=True, text=True, check=True,
        )
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", r.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "unknown"


def _count_online() -> int:
    from myfi.db.database import Database
    try:
        db     = Database()
        cutoff = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        db.cursor.execute(
            "SELECT COUNT(*) FROM devices WHERE last_seen >= ?", (cutoff,)
        )
        n = db.cursor.fetchone()[0]
        db.close()
        return n
    except Exception:
        return 0


def _count_pending() -> int:
    from myfi.db.database import Database
    try:
        db = Database()
        n  = len(db.get_pending_alerts())
        db.close()
        return n
    except Exception:
        return 0


def _db_ok() -> bool:
    from myfi.db.database import Database
    try:
        db = Database()
        db.close()
        return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════════

def setup_logging(verbosity: int) -> None:
    level = {-1: logging.WARNING, 0: logging.INFO}.get(verbosity, logging.DEBUG)
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("logs/myfi.log")],
    )


# ════════════════════════════════════════════════════════════════
# BANNER
# ════════════════════════════════════════════════════════════════

_BANNER = r"""
   ███╗   ███╗██╗   ██╗███████╗██╗
   ████╗ ████║╚██╗ ██╔╝██╔════╝██║
   ██╔████╔██║ ╚████╔╝ █████╗  ██║
   ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
   ██║ ╚═╝ ██║   ██║   ██║     ██║
   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
        network observability platform
"""


def _banner() -> None:
    console.print(_BANNER, style="myfi.cyan")


# ════════════════════════════════════════════════════════════════
# SPLASH SCREEN
# ════════════════════════════════════════════════════════════════

def show_splash_screen(engine: ChunkEngine) -> None:
    console.clear()
    _banner()

    config   = engine.config
    iface    = config.get("interface", "wlan0")
    ip       = _get_ip(iface)
    n_dev    = _count_online()
    n_chunks = len(engine._registry)
    n_alerts = _count_pending()
    db_str   = (
        "[myfi.green]ok[/myfi.green]"
        if _db_ok()
        else "[myfi.red]error[/myfi.red]"
    )

    console.rule(
        f"[bold myfi.cyan]MyFi[/bold myfi.cyan] [myfi.dim]v3.0.0-dev[/myfi.dim]",
        style="myfi.cyan",
    )

    console.print(
        f"  [myfi.dim]interface[/myfi.dim]  [myfi.cyan]{iface}[/myfi.cyan]"
        f"    [myfi.dim]ip[/myfi.dim]  [myfi.body]{ip}[/myfi.body]"
        f"    [myfi.dim]devices[/myfi.dim]  "
        f"[bold myfi.green]{n_dev} online[/bold myfi.green]"
    )

    alert_str = (
        f"[bold myfi.amber]{n_alerts} pending[/bold myfi.amber]"
        if n_alerts > 0
        else "[myfi.dim]none[/myfi.dim]"
    )
    console.print(
        f"  [myfi.dim]chunks[/myfi.dim]  [myfi.cyan]{n_chunks} active[/myfi.cyan]"
        f"    [myfi.dim]alerts[/myfi.dim]  {alert_str}"
        f"    [myfi.dim]db[/myfi.dim]  {db_str}"
    )
    console.print()


# ════════════════════════════════════════════════════════════════
# HELP
# ════════════════════════════════════════════════════════════════

def show_help(engine: ChunkEngine) -> None:
    console.clear()
    _banner()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="myfi.cyan", width=14)
    table.add_column(style="myfi.body")
    table.add_column(style="myfi.dim",  width=44)

    for cmd, desc, ex in [
        ("scan",     "Discover devices on the network (ARP)",  "scan"),
        ("monitor",  "Traffic monitoring",                     "monitor start [--live]"),
        ("limit",    "Manage usage limits",                    "limit set --mac <MAC> --daily <MB>"),
        ("chunk",    "List / enable / disable Chunks",         "chunk list"),
        ("workflow", "Run a workflow",                         "workflow run <name>"),
        ("web",      "Start web interface",                    "web"),
        ("setup",    "Configuration wizard",                   "setup"),
        ("exit",     "Exit MyFi",                              ""),
    ]:
        table.add_row(cmd, desc, ex)

    for name, chunk in engine._registry.items():
        m    = chunk.manifest()
        cmds = m.get("cli_commands", [name.lower()])
        table.add_row(
            name.lower(),
            m.get("description", name),
            cmds[0] if cmds else name.lower(),
        )

    console.print(table)
    console.print()


# ════════════════════════════════════════════════════════════════
# COMANDOS
# ════════════════════════════════════════════════════════════════

def cmd_setup(args: Any, engine: ChunkEngine) -> None:
    iface = engine.config.get("interface", "wlan0")
    for msg in [
        "[  OK  ] Loading Chunks...",
        f"[  OK  ] Mapping Interface: {iface}",
        "[  OK  ] Establishing Secure Channel: Telegram @MyFi_Bot\n",
    ]:
        console.print(f"[myfi.green]{msg}[/myfi.green]")
        sleep(0.8)
    SetupWizard(engine.config).run()


def cmd_scan(args: Any, engine: ChunkEngine) -> None:
    from myfi.db.database import Database

    config = engine.config
    if not config.is_configured():
        console.print("[myfi.red][ FAIL ] MyFi is not configured.[/myfi.red]")
        console.print("[myfi.amber]         Run: myfi setup[/myfi.amber]")
        return

    scanner  = Scanner(config)
    start_ts = datetime.now()

    with console.status("[myfi.cyan]Scanning local network...[/myfi.cyan]", spinner="dots"):
        devices = scanner.scan()

    if not devices:
        console.print("[myfi.amber][ WARN ] No devices found in ARP table.[/myfi.amber]")
        return

    db         = Database()
    today      = str(datetime.now().date())
    limits_map = {l["mac"]: l["bytes_max"] for l in db.get_limits()}
    known_macs = {d["mac"] for d in db.get_all_devices()}
    elapsed    = (datetime.now() - start_ts).total_seconds()

    console.print(
        f"\n[myfi.dim]── NETWORK MAP {'─' * 28} "
        f"[ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ][/myfi.dim]"
    )

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("STATUS",         width=10)
    table.add_column("IDENTIFICATION")
    table.add_column("IP",             width=16)
    table.add_column("USAGE TODAY",    width=22)
    table.add_column("STATE",          width=20)

    unknown_count = 0
    for d in devices:
        mac      = d["mac"]
        hostname = d["hostname"] or d["ip"]
        ip       = d["ip"]
        is_new   = mac not in known_macs

        traffic = db.get_traffic_summary(mac, since=f"{today} 00:00:00")
        used    = traffic["bytes_sent"] + traffic["bytes_recv"]
        limit   = limits_map.get(mac, 0)

        if "gateway" in (hostname or "").lower():
            status_str   = "[myfi.cyan][GATEWAY][/myfi.cyan]"
            hostname_str = f"[myfi.cyan]{hostname}[/myfi.cyan]"
        elif is_new:
            status_str   = "[bold myfi.red][ NEW   ][/bold myfi.red]"
            hostname_str = f"[bold myfi.red]{hostname or 'unknown'}[/bold myfi.red]"
            unknown_count += 1
        else:
            status_str   = "[myfi.green][ ONLINE][/myfi.green]"
            hostname_str = f"[myfi.body]{hostname}[/myfi.body]"

        if limit > 0:
            ratio = used / limit
            bar   = _fmt_bar(used, limit)
            if ratio >= 1.0:
                state = "[bold myfi.red]CRITICAL[/bold myfi.red]"
            elif ratio >= 0.8:
                state = "[myfi.amber]WARNING[/myfi.amber]"
            else:
                state = "[myfi.green]OK[/myfi.green]"
        else:
            bar, state = "[myfi.dim][ N/A ][/myfi.dim]", "[myfi.dim]OK[/myfi.dim]"

        table.add_row(
            status_str, hostname_str,
            f"[myfi.blue]{ip}[/myfi.blue]", bar, state,
        )

    db.close()
    console.print(table)

    footer = f"[myfi.dim]Total: {len(devices)} devices  ·  scan in {elapsed:.1f}s"
    footer += f"  ·  {unknown_count} unknown[/myfi.dim]" if unknown_count else "[/myfi.dim]"
    console.print(footer)

    scanner.save_to_db(devices)


def cmd_monitor(args: Any, engine: ChunkEngine) -> None:
    from myfi.core.MonitorCore import MonitorCore

    monitor = MonitorCore(engine.config)

    if args.monitor_command == "start":
        live  = getattr(args, "live", False)
        iface = engine.config.get("interface", "wlan0")

        if live:
            console.print(
                f"[myfi.cyan]LIVE STREAM[/myfi.cyan] "
                f"[myfi.dim]{iface}  ──────────────  ctrl+c to stop[/myfi.dim]"
            )
            try:
                with console.status("") as status:
                    def _cb(recv, sent, s_recv, s_sent):
                        status.update(
                            f"[myfi.dim]down[/myfi.dim]  "
                            f"[myfi.green]{_fmt_bytes(recv)}/s[/myfi.green]"
                            f"  [myfi.dim]up[/myfi.dim]  "
                            f"[myfi.cyan]{_fmt_bytes(sent)}/s[/myfi.cyan]"
                            f"  [myfi.dim]|  session down[/myfi.dim] {_fmt_bytes(s_recv)}"
                            f"  [myfi.dim]up[/myfi.dim] {_fmt_bytes(s_sent)}"
                        )
                    monitor.start(live_mode=True, interval=1, status_callback=_cb)
            except KeyboardInterrupt:
                monitor.stop()
                console.print("\n[myfi.dim]Live stream stopped.[/myfi.dim]")

        else:
            def _run():
                try:
                    monitor.start(live_mode=False, interval=300)
                except PermissionError as e:
                    console.print(f"[myfi.red][ FAIL ] {e}[/myfi.red]")
                except Exception as e:
                    logger.error(f"Monitor thread: {e}")

            t = Thread(target=_run, name="myfi-monitor", daemon=True)
            t.start()
            console.print(
                "[myfi.green][  >>  ] Monitor started in background "
                "(5 min interval).[/myfi.green]"
            )
            console.print(
                "[myfi.dim]         Run 'monitor stop' to stop.[/myfi.dim]"
            )

    elif args.monitor_command == "stop":
        monitor.stop()
        console.print("[myfi.red][ STOP ] Monitor stopped.[/myfi.red]")

    elif args.monitor_command == "report":
        from myfi.db.database import Database
        db      = Database()
        summary = db.get_traffic_summary(monitor.my_mac)
        console.print("\n[myfi.dim]── USAGE REPORT ── [ Last 24h ][/myfi.dim]")
        console.print(
            f"  [myfi.dim]received[/myfi.dim]  "
            f"[myfi.green]{_fmt_bytes(summary['bytes_recv'])}[/myfi.green]"
            f"    [myfi.dim]sent[/myfi.dim]  "
            f"[myfi.cyan]{_fmt_bytes(summary['bytes_sent'])}[/myfi.cyan]"
        )
        db.close()
    else:
        console.print(
            "[myfi.red][ FAIL ] Invalid subcommand: start | stop | report[/myfi.red]"
        )


def cmd_limit(args: Any, engine: ChunkEngine) -> None:
    from myfi.db.database import Database

    db = Database()

    if args.limit_command == "set":
        if not args.daily:
            console.print("[myfi.red][ FAIL ] Specify --daily <MB>.[/myfi.red]")
            db.close()
            return

        bytes_limit = args.daily * 1024 * 1024
        existing    = db.get_limits(args.mac)

        if existing:
            old_mb = existing[0]["bytes_max"] / (1024 * 1024)
            console.print(
                f"\n[myfi.amber][ WARN ] '{args.mac}' already has a limit of "
                f"{old_mb:.0f} MB.[/myfi.amber]"
            )
            if not Confirm.ask(f"Change to {args.daily} MB?"):
                console.print("[myfi.dim]Operation cancelled.[/myfi.dim]")
                db.close()
                return

        db.save_device(args.mac, "Unknown", "0.0.0.0")
        db.set_limit(args.mac, "daily", bytes_limit)
        console.print(
            f"[myfi.green][  OK  ] Limit set:[/myfi.green]"
            f" [myfi.body]{args.mac}[/myfi.body]"
            f" [myfi.dim]->[/myfi.dim]"
            f" [bold myfi.green]{args.daily} MB/day[/bold myfi.green]"
        )

    elif args.limit_command == "show":
        limits = db.get_limits()
        if not limits:
            console.print("[myfi.dim]No limits configured.[/myfi.dim]")
            db.close()
            return

        today = str(datetime.now().date())
        console.print("\n[myfi.dim]── QUOTA MANAGEMENT ── [ ACTIVE LIMITS ][/myfi.dim]")

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("IDENTIFIER", style="myfi.body")
        table.add_column("TYPE",       style="myfi.cyan")
        table.add_column("LIMIT",      style="myfi.green")
        table.add_column("USAGE",      style="myfi.body")
        table.add_column("PROGRESS",   style="bold")

        for limit in limits:
            mb      = limit["bytes_max"] / (1024 * 1024)
            traffic = db.get_traffic_summary(limit["mac"], since=f"{today} 00:00:00")
            used_mb = (traffic["bytes_sent"] + traffic["bytes_recv"]) / (1024 * 1024)
            bar     = _fmt_bar(int(used_mb * 1024 * 1024), limit["bytes_max"])
            ratio   = used_mb / mb if mb > 0 else 0
            prog    = f"{bar} {ratio*100:.0f}%"
            if ratio >= 1.0:
                prog += " [bold myfi.red][CRIT][/bold myfi.red]"
            table.add_row(
                limit["mac"], limit["limit_type"],
                f"{mb:.0f} MB", f"{used_mb:.0f} MB", prog,
            )
        console.print(table)

    elif args.limit_command == "remove":
        db.remove_limit(args.mac)
        console.print(f"[myfi.green][  OK  ] Limit removed:[/myfi.green] {args.mac}")
    else:
        console.print(
            "[myfi.red][ FAIL ] Invalid subcommand: set | show | remove[/myfi.red]"
        )

    db.close()


def cmd_chunk(args: Any, engine: ChunkEngine) -> None:
    if args.chunk_command == "list":
        if not engine._registry:
            console.print("[myfi.dim]No Chunks registered.[/myfi.dim]")
            return

        console.print("\n[myfi.dim]── MYFI CHUNKS ── [ REGISTERED MODULES ][/myfi.dim]")
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("STATE",    width=8)
        table.add_column("NAME",     style="myfi.body")
        table.add_column("VERSION",  style="myfi.dim")
        table.add_column("FUNCTION", style="myfi.cyan")

        for name, chunk in engine._registry.items():
            m     = chunk.manifest()
            state = (
                "[myfi.green][ ON ][/myfi.green]"
                if chunk.enabled
                else "[myfi.dim][ OFF][/myfi.dim]"
            )
            table.add_row(state, name, m.get("version", "?"), m.get("description", ""))
        console.print(table)

    elif args.chunk_command == "enable":
        if engine.is_registered(args.name):
            engine.enable(args.name)
            console.print(f"[myfi.green][  OK  ] Chunk '{args.name}' enabled.[/myfi.green]")
        else:
            console.print(f"[myfi.red][ FAIL ] Chunk '{args.name}' not found.[/myfi.red]")

    elif args.chunk_command == "disable":
        if engine.is_registered(args.name):
            engine.disable(args.name)
            console.print(f"[myfi.amber][ WARN ] Chunk '{args.name}' disabled.[/myfi.amber]")
        else:
            console.print(f"[myfi.red][ FAIL ] Chunk '{args.name}' not found.[/myfi.red]")
    else:
        console.print(
            "[myfi.red][ FAIL ] Invalid subcommand: list | enable | disable[/myfi.red]"
        )


def cmd_workflow(args: Any, engine: ChunkEngine) -> None:
    if args.workflow_command != "run":
        console.print("[myfi.red][ FAIL ] Invalid subcommand: run[/myfi.red]")
        return

    wf_file = Path("config/workflows.json")
    if not wf_file.exists():
        console.print(f"[myfi.red][ FAIL ] File not found: {wf_file}[/myfi.red]")
        return

    try:
        workflows = json.loads(wf_file.read_text())
    except Exception as e:
        console.print(f"[myfi.red][ FAIL ] Error reading workflows: {e}[/myfi.red]")
        return

    if args.name not in workflows:
        console.print(f"[myfi.red][ FAIL ] Workflow '{args.name}' does not exist.[/myfi.red]")
        return

    steps = workflows[args.name].get("steps", [])

    try:
        engine.define_workflow(args.name, steps)
    except ValueError as e:
        console.print(f"[myfi.red][ FAIL ] {e}[/myfi.red]")
        return

    states: list[dict] = [{"name": s, "status": "pending", "detail": ""} for s in steps]

    def _render() -> Text:
        t = Text()
        for s in states:
            st = s["status"]
            if st == "done":
                dot, style = "●", "myfi.green"
            elif st == "running":
                dot, style = "◌", "myfi.cyan"
            elif st == "failed":
                dot, style = "x", "myfi.red"
            elif st == "skipped":
                dot, style = "○", "myfi.amber"
            else:
                dot, style = "○", "myfi.dim"
            t.append(f"  {dot} ", style=f"bold {style}")
            t.append(f"{s['name'].ljust(30)}", style=style)
            t.append(f"  {s['detail']}\n", style="myfi.dim")

        done_n  = sum(1 for s in states if s["status"] == "done")
        total_n = len(states)
        filled  = int(20 * done_n / total_n) if total_n else 0
        bar     = "█" * filled + "░" * (20 - filled)
        t.append("\n  progress  ", style="myfi.dim")
        t.append(bar, style="myfi.cyan")
        t.append(f"  {done_n} / {total_n} chunks\n", style="myfi.dim")
        return t

    console.print(
        f"\n[myfi.dim]── WORKFLOW ENGINE {'─' * 18}[/myfi.dim]"
        f" [bold myfi.cyan][ {args.name} ][/bold myfi.cyan]"
    )

    data:   dict = {}
    start        = datetime.now()
    failed       = False

    with Live(_render(), refresh_per_second=10, console=console) as live:
        for i, step in enumerate(steps):
            states[i]["status"] = "running"
            states[i]["detail"] = "executing..."
            live.update(_render())

            chunk = engine._registry.get(step)
            if chunk is None or not chunk.enabled:
                states[i]["status"] = "skipped"
                states[i]["detail"] = "disabled"
                live.update(_render())
                continue

            try:
                data = chunk.run(data)
                states[i]["status"] = "done"
                states[i]["detail"] = "completed"
                live.update(_render())
            except Exception as e:
                states[i]["status"] = "failed"
                states[i]["detail"] = str(e)
                live.update(_render())
                failed = True
                break

    elapsed = (datetime.now() - start).total_seconds()
    done_n  = sum(1 for s in states if s["status"] == "done")
    skip_n  = sum(1 for s in states if s["status"] == "skipped")

    if failed:
        console.print(
            f"[myfi.red][ FAIL ] Workflow '{args.name}' failed in {elapsed:.1f}s.[/myfi.red]"
        )
    else:
        detail = f"  {done_n} executed"
        if skip_n:
            detail += f"  ·  {skip_n} skipped"
        console.print(
            f"[myfi.green][  OK  ] Workflow '{args.name}' completed in {elapsed:.1f}s."
            f"[/myfi.green][myfi.dim]{detail}[/myfi.dim]"
        )


def cmd_web(args: Any, engine: ChunkEngine) -> None:
    from myfi.ui.web.app import app

    ip = _get_ip(engine.config.get("interface", "wlan0"))
    console.print("\n[myfi.dim]── MYFI WEB INTERFACE ── [ STARTING ][/myfi.dim]")
    console.print(f"  [myfi.dim]local[/myfi.dim]    [myfi.blue]http://localhost:5000[/myfi.blue]")
    console.print(f"  [myfi.dim]network[/myfi.dim]  [myfi.blue]http://{ip}:5000[/myfi.blue]")
    console.print("  [myfi.dim]ctrl+c to stop[/myfi.dim]\n")
    app.run(debug=False)


# ════════════════════════════════════════════════════════════════
# DESPACHO
# ════════════════════════════════════════════════════════════════

_HANDLERS: dict[str, Any] = {
    "setup":    cmd_setup,
    "scan":     cmd_scan,
    "monitor":  cmd_monitor,
    "limit":    cmd_limit,
    "chunk":    cmd_chunk,
    "workflow": cmd_workflow,
    "web":      cmd_web,
}


def dispatch_command(args: Any, engine: ChunkEngine) -> None:
    handler = _HANDLERS.get(args.command)
    if handler:
        handler(args, engine)
        return
    chunk_handler = engine.get_cli_handler(args.command)
    if chunk_handler:
        chunk_handler(args)
    else:
        console.print(f"[myfi.red][ FAIL ] Unknown command: '{args.command}'[/myfi.red]")


# ════════════════════════════════════════════════════════════════
# SHELL INTERATIVA
# ════════════════════════════════════════════════════════════════

def interactive_shell(engine: ChunkEngine, parser: argparse.ArgumentParser) -> None:
    console.print("[myfi.dim]'help' for commands  ·  'exit' to quit[/myfi.dim]\n")

    while True:
        try:
            user_input = Prompt.ask(
                "[bold myfi.cyan]myfi[/bold myfi.cyan] [myfi.cyan]>[/myfi.cyan]"
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[myfi.dim]Exiting MyFi...[/myfi.dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[myfi.dim]Goodbye.[/myfi.dim]")
            break
        if user_input.lower() == "help":
            show_help(engine)
            continue

        try:
            parsed = parser.parse_args(shlex.split(user_input))
            if parsed.command:
                dispatch_command(parsed, engine)
        except SystemExit:
            pass
        except Exception as e:
            console.print(f"[myfi.red][ FAIL ] {e}[/myfi.red]")


# ════════════════════════════════════════════════════════════════
# PARSER
# ════════════════════════════════════════════════════════════════

def build_parser() -> tuple[argparse.ArgumentParser, Any]:
    p = argparse.ArgumentParser(prog="myfi", add_help=False)
    p.add_argument("-h", "--help",    action="store_true")
    p.add_argument("-V", "--version", action="store_true")

    vg = p.add_mutually_exclusive_group()
    vg.add_argument("-q", "--quiet",   action="store_true")
    vg.add_argument("-v", "--verbose", action="store_true")
    vg.add_argument("-vv",             action="store_true")

    sub = p.add_subparsers(dest="command")
    sub.add_parser("setup")
    sub.add_parser("scan")
    sub.add_parser("web")

    mon     = sub.add_parser("monitor")
    mon_sub = mon.add_subparsers(dest="monitor_command")
    ms      = mon_sub.add_parser("start")
    ms.add_argument("--live", action="store_true")
    mon_sub.add_parser("stop")
    mon_sub.add_parser("report")

    lim     = sub.add_parser("limit")
    lim_sub = lim.add_subparsers(dest="limit_command")
    ls      = lim_sub.add_parser("set")
    ls.add_argument("--mac",   required=True)
    ls.add_argument("--daily", type=int)
    lim_sub.add_parser("show")
    lr = lim_sub.add_parser("remove")
    lr.add_argument("--mac", required=True)

    chk     = sub.add_parser("chunk")
    chk_sub = chk.add_subparsers(dest="chunk_command")
    chk_sub.add_parser("list")
    ce = chk_sub.add_parser("enable");  ce.add_argument("name")
    cd = chk_sub.add_parser("disable"); cd.add_argument("name")

    wf     = sub.add_parser("workflow")
    wf_sub = wf.add_subparsers(dest="workflow_command")
    wr     = wf_sub.add_parser("run")
    wr.add_argument("name")

    return p, sub


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main() -> None:
    parser, subparsers = build_parser()
    engine = _create_engine()
    discover_and_register_chunks(engine, subparsers)
    args = parser.parse_args()

    if args.quiet:     setup_logging(-1)
    elif args.vv:      setup_logging(2)
    elif args.verbose: setup_logging(1)
    else:              setup_logging(0)

    if args.version:
        console.print(
            "[bold myfi.cyan]MyFi[/bold myfi.cyan] Network Engine"
            "  [myfi.dim]v3.0.0-dev[/myfi.dim]"
        )
        console.print(f"[myfi.dim]registered chunks: {len(engine._registry)}[/myfi.dim]")
        console.print("[myfi.green][  OK  ] system operational[/myfi.green]")
        sys.exit(0)

    if args.help:
        show_help(engine)
        sys.exit(0)

    if not args.command:
        show_splash_screen(engine)
        interactive_shell(engine, parser)
        sys.exit(0)

    try:
        dispatch_command(args, engine)
    except KeyboardInterrupt:
        console.print("\n[myfi.dim]Interrupted.[/myfi.dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[myfi.red][ FAIL ] {e}[/myfi.red]")
        console.print("[myfi.dim]Check hardware or run 'myfi setup'.[/myfi.dim]")
        logger.exception("Unhandled error in main()")
        sys.exit(1)


if __name__ == "__main__":
    main()
