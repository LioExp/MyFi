import sys
import argparse
import logging
from rich.console import Console
from rich.table import Table
from datetime import datetime
from myfi.core.config_manager import ConfigManager
from myfi.core.scanner import Scanner
from myfi.ui.cli.setup_wizard import SetupWizard

console = Console()

def _format_bytes(num_bytes: int) -> str:
    """Formata bytes para uma unidade legível."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} TB"

def setup_logging(verbosity: int):
    """Configura o logging para ficheiro. O terminal fica limpo para a UI."""
    import os
    from pathlib import Path

    if verbosity <= -1:
        level = logging.WARNING
    elif verbosity == 0:
        level = logging.INFO
    else:
        level = logging.DEBUG

    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_dir / 'myfi.log'),
        ]
    )

def show_banner():
    """Exibe o banner ASCII do MyFi."""
    ascii_art = r"""
    ███╗   ███╗██╗   ██╗███████╗██╗
    ████╗ ████║╚██╗ ██╔╝██╔════╝██║
    ██╔████╔██║ ╚████╔╝ █████╗  ██║
    ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
    ██║ ╚═╝ ██║   ██║   ██║     ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
    """
    console.print(ascii_art, style="bold cyan")
    console.print("MyFi - Intelligent Network Monitor", style="bold white underline")
    console.print()

def show_help():
    """Mostra a ajuda personalizada."""
    console.clear()
    show_banner()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=10)
    table.add_column(style="white")
    table.add_column(style="dim", width=40)

    table.add_row("setup", "Run the configuration wizard", "")
    table.add_row("scan", "Scan the network for devices", "[dim]myfi scan [-v][/dim]")
    table.add_row("monitor", "Start/stop traffic monitoring", "[dim]myfi monitor start [--live][/dim]")
    table.add_row("limit", "Manage device limits", "[dim]myfi limit set --mac ...[/dim]")

    console.print(table)
    console.print()
    console.print("Usage: [bold]myfi <command> [options][/bold]", style="dim")
    console.print("Example: [dim]$ myfi scan -v[/dim]")

def cmd_setup(args):
    """Comando setup."""
    config = ConfigManager()
    wizard = SetupWizard(config)
    wizard.run()

def cmd_scan(args):
    """Comando scan."""
    config = ConfigManager()
    if not config.is_configured():
        console.print("[red]✗ MyFi is not configured.[/red]")
        console.print("[yellow]Please run [bold]myfi setup[/bold] first.[/yellow]")
        sys.exit(1)

    scanner = Scanner(config)
    dispositivos = scanner.scan()

    # Exibir com rich (tabela)
    from rich.table import Table as RichTable
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table = RichTable(
        title=f"Network Scan – {timestamp}",
        title_style="bold white",
        box=None,
        show_header=True,
        header_style="bold cyan",
        padding=(0, 2)
    )
    table.add_column("Hostname", style="cyan")
    table.add_column("IP", style="white")
    table.add_column("MAC", style="green")
    table.add_column("Interface", style="dim white")

    for d in dispositivos:
        table.add_row(d['hostname'], d['ip'], d['mac'], d['interface'])

    console.print(table)
    console.print(f"[dim]Total devices: {len(dispositivos)}[/dim]")

    # Salvar na BD (opcional)
    scanner.save_to_db(dispositivos)

def cmd_monitor(args):
    """Comando monitor (start/stop/report)."""
    from myfi.core.MonitorCore import MonitorCore
    from myfi.db.database import Database

    config = ConfigManager()
    monitor_core = MonitorCore(config)

    if args.monitor_command == 'start':
        live = getattr(args, 'live', False)
        console.print(f"[green]▶ Starting monitor...[/green]")
        if live:
            console.print("[yellow]Live mode (1s interval)[/yellow]")
            monitor_core.start(live_mode=True, interval=1)
        else:
            console.print("[dim]Low Power mode (5 min interval)[/dim]")
            monitor_core.start(live_mode=False, interval=300)
    elif args.monitor_command == 'stop':
        monitor_core.stop()
        console.print("[red]⏹️ Monitor stopped.[/red]")
    elif args.monitor_command == 'report':
        db = Database()
        summary = db.get_traffic_summary(monitor_core.my_mac)
        console.print(f"[cyan]📊 Traffic summary for {monitor_core.my_mac}:[/cyan]")
        console.print(f"↓ {_format_bytes(summary['bytes_recv'])}  ↑ {_format_bytes(summary['bytes_sent'])}")
        db.close()
    else:
        console.print("[red]✗ Missing monitor subcommand (start/stop/report).[/red]")

def cmd_limit(args):
    """Comando limit (set/show/remove)."""
    from myfi.db.database import Database
    db = Database()

    if args.limit_command == 'set':
        if args.daily:
            bytes_limit = args.daily * 1024 * 1024
            limit_type = 'daily'
        else:
            console.print("[red]✗ Please specify a limit type (e.g., --daily 200).[/red]")
            return

        db.save_device(args.mac, 'Unknown', '0.0.0.0')
        db.set_limit(args.mac, limit_type, bytes_limit)
        console.print(f"[green]✓ Limit set for {args.mac}: {args.daily} MB per day.[/green]")

    elif args.limit_command == 'show':
        limits = db.get_limits()
        if not limits:
            console.print("[yellow]No limits configured.[/yellow]")
            return

        table = Table(title="Active Limits", box=None, header_style="bold cyan")
        table.add_column("MAC", style="white")
        table.add_column("Type", style="cyan")
        table.add_column("Limit (MB)", style="green")

        for limit in limits:
            mb = limit['bytes_max'] / (1024 * 1024)
            table.add_row(limit['mac'], limit['limit_type'], f"{mb:.0f}")
        console.print(table)

    elif args.limit_command == 'remove':
        db.remove_limit(args.mac)
        console.print(f"[green]✓ Limits removed for {args.mac}.[/green]")

    else:
        console.print("[red]✗ Missing limit subcommand (set/show/remove).[/red]")

    db.close()

def main():
    parser = argparse.ArgumentParser(
        prog="myfi",
        description="MyFi - Intelligent Network Monitor",
        add_help=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    # A verbosidade é capturada pelo parser principal e aplicada globalmente
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    verbosity.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    verbosity.add_argument('-vv', action='store_true', help='Very verbose mode')

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("setup", help="Run configuration wizard")
    subparsers.add_parser("scan", help="Scan network for devices")

    monitor_parser = subparsers.add_parser("monitor", help="Monitor traffic")
    monitor_sub = monitor_parser.add_subparsers(dest="monitor_command")
    monitor_start = monitor_sub.add_parser("start", help="Start monitoring")
    monitor_start.add_argument("--live", action="store_true", help="Live mode (1s interval)")
    monitor_sub.add_parser("stop", help="Stop monitoring")
    monitor_sub.add_parser("report", help="Show traffic report")

    limit_parser = subparsers.add_parser("limit", help="Manage device limits")
    limit_sub = limit_parser.add_subparsers(dest="limit_command")
    limit_set = limit_sub.add_parser("set", help="Set a limit")
    limit_set.add_argument("--mac", required=True, help="Device MAC address")
    limit_set.add_argument("--daily", type=int, help="Daily limit in MB")
    limit_sub.add_parser("show", help="Show all limits")
    limit_remove = limit_sub.add_parser("remove", help="Remove a limit")
    limit_remove.add_argument("--mac", required=True, help="Device MAC address")

    args = parser.parse_args()

    if args.help or not args.command:
        show_help()
        sys.exit(0)

    # Configurar logging com base nas flags principais
    if args.quiet:
        setup_logging(-1)
    elif args.vv:
        setup_logging(2)
    elif args.verbose:
        setup_logging(1)
    else:
        setup_logging(0)

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "limit":
        cmd_limit(args)
    else:
        show_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user.[/yellow]")
        sys.exit(0)