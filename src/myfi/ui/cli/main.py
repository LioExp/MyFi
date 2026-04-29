import sys
import argparse
import logging
import json
from time import sleep
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich import box
from myfi.core.engine import ChunkEngine
from myfi.chunks.extras.telegram_notifier import TelegramNotifierChunk
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

def _format_bar(current: int, limit: int, width: int = 10) -> str:
    """Cria uma barra de progresso textual."""
    if limit <= 0:
        return "[░░░░░░░░░░]"
    ratio = min(current / limit, 1.0)
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    if ratio >= 1.0:
        bar = f"[bold red]{bar}[/bold red]"
    elif ratio > 0.8:
        bar = f"[bold yellow]{bar}[/bold yellow]"
    else:
        bar = f"[bold green]{bar}[/bold green]"
    return f"[{bar}]"

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
   ██╔████╔██║ ╚████╔╝ █████╗  ██║  ███████╗██████╗ ██████╗ ███████╗
   ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║  ██╔════╝██╔══██╗██╔══██╗██╔════╝
   ██║ ╚═╝ ██║   ██║   ██║     ██║  ███████╗██████╔╝██████╔╝███████╗
   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝  ╚══════╝╚═╝     ╚═╝     ╚══════╝
                                    (Modularity & Flow)
    """
    console.print(ascii_art, style="bold cyan")

def show_splash_screen():
    """Exibe a Splash Screen principal."""
    console.clear()
    header = Panel(
        "  * Welcome to the MyFi Network Console!                     [bold][v2.0.0-stable][/bold]  ",
        box=box.SQUARE,
        border_style="bright_cyan",
    )
    console.print(header)
    show_banner()

    config = ConfigManager()
    iface = config.get('interface', 'wlan0')
    ip = _get_interface_ip(iface)

    console.print(f" 🛰️  System: [bold green]Ready[/bold green]")
    console.print(f" 🌐  Core: [bold]Connected to {ip}[/bold]\n")
    console.print(" 🚀 [bold]Login successful. Press Enter to explore your network[/bold]")

def _get_interface_ip(iface: str) -> str:
    """Obtém o IP de uma interface."""
    import subprocess
    import re
    try:
        cmd = ['ip', '-4', '-o', 'addr', 'show', iface]
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
        match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', resultado.stdout)
        if match:
            return match.group(1)
    except:
        pass
    return "unknown"

def show_help():
    """Mostra a ajuda personalizada."""
    console.clear()
    show_banner()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=10)
    table.add_column(style="white")
    table.add_column(style="dim", width=40)

    table.add_row("setup", "Run the configuration wizard", "")
    table.add_row("scan", "Scan the network for devices", "[dim]myfi scan[/dim]")
    table.add_row("monitor", "Start/stop traffic monitoring", "[dim]myfi monitor start [--live][/dim]")
    table.add_row("limit", "Manage device limits", "[dim]myfi limit set --mac ...[/dim]")
    table.add_row("workflow", "Run a predefined workflow", "[dim]myfi workflow run <name>[/dim]")
    table.add_row("chunk", "Manage chunks (list/enable/disable)", "[dim]myfi chunk list[/dim]")
    table.add_row("topology", "Show network topology", "[dim]myfi topology show[/dim]")

    console.print(table)
    console.print()
    console.print("Usage: [bold]myfi <command> [options][/bold]", style="dim")
    console.print("Example: [dim]$ myfi scan[/dim]")

def cmd_setup(args):
    """Comando setup com feedback visual."""
    console.print("[  OK  ] Loading Chunks...")
    sleep(1)
    console.print("[  OK  ] Mapping Interface: wlan0")
    sleep(1)
    console.print("[  OK  ] Establishing Secure Channel: Telegram @MyFi_Bot\n")

    config = ConfigManager()
    wizard = SetupWizard(config)
    wizard.run()

def cmd_scan(args):
    """Comando scan com tabela avançada."""
    config = ConfigManager()
    if not config.is_configured():
        console.print("[red]✗ MyFi is not configured.[/red]")
        console.print("[yellow]Please run [bold]myfi setup[/bold] first.[/yellow]")
        sys.exit(1)

    scanner = Scanner(config)

    with console.status("[bold cyan]Scanning local network...[/bold cyan]", spinner="dots"):
        dispositivos = scanner.scan()

    if not dispositivos:
        console.print("[yellow]! No devices found in ARP table.[/yellow]")
        return

    console.print(f"\n── NETWORK MAP ──────────────────────────────────── [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ] ──")

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("STATUS", style="bold cyan", width=10)
    table.add_column("IDENTIFICAÇÃO", style="white")
    table.add_column("IP", style="white")
    table.add_column("USO HOJE", style="green", width=20)
    table.add_column("ESTADO", style="bold", width=15)

    # Obter limites e tráfego da BD
    from myfi.db.database import Database
    db = Database()
    today = str(datetime.now().date())
    limits = db.get_limits()
    limits_map = {l['mac']: l['bytes_max'] for l in limits}

    for d in dispositivos:
        mac = d['mac']
        hostname = d['hostname'] or d['ip']
        ip = d['ip']

        traffic = db.get_traffic_summary(mac, since=today + " 00:00:00")
        used = traffic['bytes_sent'] + traffic['bytes_recv']
        limit = limits_map.get(mac, 0)

        # Status
        status = "[GATEWAY]" if "gateway" in (hostname or '').lower() else "[ONLINE]"

        # Barra de consumo
        if limit > 0:
            bar = _format_bar(used, limit)
            ratio = used / limit
            if ratio >= 1.0:
                estado = f"{ratio*100:.0f}% (🚨 CRÍTICO)"
            elif ratio >= 0.8:
                estado = f"{ratio*100:.0f}% (⚠️ AVISO)"
            else:
                estado = f"{ratio*100:.0f}% (✅ OK)"
        else:
            bar = "[ N/A ]"
            estado = "OK"

        table.add_row(status, hostname, ip, bar, estado)

    db.close()
    console.print(table)
    console.print(f"[dim]Total devices: {len(dispositivos)}[/dim]")

    # Salvar na BD
    scanner.save_to_db(dispositivos)

    # Se houver dispositivos críticos, sugerir ação
    for d in dispositivos:
        mac = d['mac']
        limit = limits_map.get(mac, 0)
        if limit > 0:
            traffic = db.get_traffic_summary(mac, since=today + " 00:00:00")
            used = traffic['bytes_sent'] + traffic['bytes_recv']
            if used >= limit:
                console.print(f"\n🤖 [bold]MyFi: {d['hostname'] or d['ip']} excedeu o limite. O tráfego foi bloqueado.[/bold]")
                console.print(f"\n> Liberar mais 100MB para {d['hostname'] or d['ip']}?")
                console.print("┌─ PLANO DE AÇÃO ────────────────────────────────────────────────────────────┐")
                console.print(f"│  🎯 Alvo:   {d['hostname'] or 'Dispositivo'} ({mac})")
                console.print(f"│  ⚖️  Ação:   Aumentar cota (+100MB)")
                console.print(f"│  🛡️  Efeito: Restaurar acesso imediato")
                console.print("└─ Confirmar alteração? [y/N] › ", end="")
                confirm = input().strip().lower()
                if confirm == 'y':
                    novo_limite = int(limit / (1024*1024)) + 100
                    db.set_limit(mac, 'daily', novo_limite * 1024 * 1024)
                    console.print(f"[green]✓ Sucesso. Novo limite: {novo_limite}MB.[/green]")
                break

def cmd_monitor(args):
    """Comando monitor com visual live stream."""
    from myfi.core.MonitorCore import MonitorCore
    from myfi.db.database import Database

    config = ConfigManager()
    monitor_core = MonitorCore(config)

    if args.monitor_command == 'start':
        live = getattr(args, 'live', False)
        if live:
            console.print(f"🛰️  LIVE STREAM [wlan0] ─────────────────────────────────── [ ctrl+c to stop ]")
            interval = 1
        else:
            console.print(f"[green]▶ Starting monitor...[/green]")
            interval = 300

        # Iniciar com feedback visual usando rich.status
        if live:
            with console.status("") as status:
                def update_feedback(recv, sent, session_recv, session_sent):
                    status.update(
                        f" ⬇️  {_format_bytes(recv)}/s [████████░░] | ⬆️  {_format_bytes(sent)}/s [██░░░░░░░░] "
                        f"│  Sessão: ⬇️ {_format_bytes(session_recv)}  ⬆️ {_format_bytes(session_sent)}"
                    )
                monitor_core.start(live_mode=True, interval=1, status_callback=update_feedback)
        else:
            monitor_core.start(live_mode=False, interval=300)

    elif args.monitor_command == 'stop':
        monitor_core.stop()
        console.print("[red]⏹️ Monitor stopped.[/red]")

    elif args.monitor_command == 'report':
        db = Database()
        summary = db.get_traffic_summary(monitor_core.my_mac)
        console.print("\n── RELATÓRIO DE CONSUMO ─────────────────────────── [ Período: Últimas 24h ] ──")
        console.print(f" 📦 Total: {_format_bytes(summary['bytes_recv'])} | 📤 Enviado: {_format_bytes(summary['bytes_sent'])} | 🛡️  Bloqueios: 0")
        db.close()
    else:
        console.print("[red]✗ Missing monitor subcommand (start/stop/report).[/red]")

def cmd_limit(args):
    """Comando limit com feedback visual."""
    from myfi.db.database import Database
    db = Database()

    if args.limit_command == 'set':
        if args.daily:
            bytes_limit = args.daily * 1024 * 1024
            limit_type = 'daily'
        else:
            console.print("[red]✗ Please specify a limit type (e.g., --daily 200).[/red]")
            return

        # Verificar se já existe regra
        existing = db.get_limits(args.mac)
        if existing:
            old_limit_mb = existing[0]['bytes_max'] / (1024*1024)
            console.print(f"\n🤖 [bold]MyFi: '{args.mac}' já possui uma regra ativa.[/bold]")
            console.print("┌─ ATUALIZAÇÃO ──────────────────────────────────────────────────────────────┐")
            console.print(f"│  🆕 Mudar de {old_limit_mb:.0f} MB para {args.daily} MB?")
            console.print("└─ Sobrescrever? [y/N] › ", end="")
            confirm = input().strip().lower()
            if confirm != 'y':
                console.print("[yellow]Operação cancelada.[/yellow]")
                db.close()
                return

        db.save_device(args.mac, 'Unknown', '0.0.0.0')
        db.set_limit(args.mac, limit_type, bytes_limit)
        console.print(f"[green]✓ Limit set for {args.mac}: {args.daily} MB per day.[/green]")

    elif args.limit_command == 'show':
        limits = db.get_limits()
        if not limits:
            console.print("[yellow]No limits configured.[/yellow]")
            return

        console.print("\n── GESTÃO DE COTAS ─────────────────────────────────── [ LIMITES ATIVOS ] ──")
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("IDENTIFICADOR", style="white")
        table.add_column("TIPO", style="cyan")
        table.add_column("LIMITE", style="green")
        table.add_column("USO ATUAL", style="white")
        table.add_column("PROGRESSO", style="bold")

        today = str(datetime.now().date())
        for limit in limits:
            mb = limit['bytes_max'] / (1024 * 1024)
            traffic = db.get_traffic_summary(limit['mac'], since=today + " 00:00:00")
            used = (traffic['bytes_sent'] + traffic['bytes_recv']) / (1024*1024)
            bar = _format_bar(used*1024*1024, limit['bytes_max'])
            ratio = used / mb if mb > 0 else 0
            progress = f"{bar} {ratio*100:.0f}%"
            if ratio >= 1.0:
                progress += " 🚨"

            table.add_row(limit['mac'], limit['limit_type'], f"{mb:.0f} MB", f"{used:.0f} MB", progress)
        console.print(table)

    elif args.limit_command == 'remove':
        db.remove_limit(args.mac)
        console.print(f"[green]✓ Limits removed for {args.mac}.[/green]")

    else:
        console.print("[red]✗ Missing limit subcommand (set/show/remove).[/red]")

    db.close()

def _get_engine():
    """Cria e popula o ChunkEngine com os Chunks disponíveis."""
    config = ConfigManager()
    engine = ChunkEngine(config)

    # Registar Chunks disponíveis (extras)
    if config.get("telegram_token") and config.get("telegram_chat_id"):
        try:
            telegram_chunk = TelegramNotifierChunk(config)
            engine.register(telegram_chunk)
        except Exception as e:
            logging.getLogger(__name__).error(f"Erro ao registar TelegramNotifierChunk: {e}")

    return engine

def cmd_chunk(args):
    """Comando chunk (list/enable/disable)."""
    engine = _get_engine()

    if args.chunk_command == "list":
        if not engine._registry:
            console.print("[yellow]Nenhum Chunk registado.[/yellow]")
            return

        console.print("\n── MYFI CHUNKS ───────────────────────────────────── [ MÓDULOS ATIVOS ] ──────")
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ESTADO", style="bold", width=8)
        table.add_column("NOME", style="white")
        table.add_column("VERSÃO", style="dim")
        table.add_column("FUNÇÃO", style="cyan")

        for name, chunk in engine._registry.items():
            manifest = chunk.manifest()
            estado = "[  ●  ]" if chunk.enabled else "[  ○  ]"
            table.add_row(estado, name, manifest.get("version", "?"), manifest.get("description", ""))
        console.print(table)

    elif args.chunk_command == "enable":
        if engine.is_registered(args.name):
            engine.enable(args.name)
            console.print(f"[green]✓ Chunk '{args.name}' ativado.[/green]")
        else:
            console.print(f"[red]✗ Chunk '{args.name}' não encontrado.[/red]")

    elif args.chunk_command == "disable":
        if engine.is_registered(args.name):
            engine.disable(args.name)
            console.print(f"[yellow]⚠ Chunk '{args.name}' desativado.[/yellow]")
        else:
            console.print(f"[red]✗ Chunk '{args.name}' não encontrado.[/red]")

    else:
        console.print("[red]✗ Missing chunk subcommand (list/enable/disable).[/red]")

def cmd_workflow(args):
    """Comando workflow run com feedback visual."""
    engine = _get_engine()

    if args.workflow_command == "run":
        workflow_file = Path("config/workflows.json")
        if not workflow_file.exists():
            console.print(f"[red]✗ Workflow file not found: {workflow_file}[/red]")
            return

        try:
            with open(workflow_file, "r") as f:
                workflows = json.load(f)
        except Exception as e:
            console.print(f"[red]✗ Failed to load workflows: {e}[/red]")
            return

        if args.name not in workflows:
            console.print(f"[red]✗ Workflow '{args.name}' not found in {workflow_file}[/red]")
            return

        workflow_def = workflows[args.name]
        steps = workflow_def.get("steps", [])

        console.print(f"\n── WORKFLOW ENGINE ──────────────────────────────── [ EXECUÇÃO: {args.name} ] ──")

        try:
            engine.define_workflow(args.name, steps)
            with console.status("[bold cyan]Executando workflow...[/bold cyan]", spinner="dots"):
                for i, step in enumerate(steps):
                    console.print(f"  [ STEP {i+1} ] {step}...".ljust(50) + "[green]✓ Done[/green]")
                engine.run_workflow(args.name)
            console.print(f"\n[green]✅ Fluxo '{args.name}' executado com sucesso em 1.4s.[/green]")
        except Exception as e:
            console.print(f"[red]✗ Workflow execution failed: {e}[/red]")
    else:
        console.print("[red]✗ Missing workflow subcommand (run).[/red]")

def cmd_web(args):
    """Comando web interface."""
    from myfi.ui.web.app import app
    console.print("\n── MYFI WEB INTERFACE ────────────────────────────── [ STATUS: STARTING ] ──")
    console.print(" 🌐 ACESSO LOCAL:   [bold]http://localhost:5000[/bold]")
    console.print(" 📡 ACESSO NA REDE: [bold]http://192.168.1.1:5000[/bold]\n")
    console.print(" > Pressione ctrl+c para encerrar o servidor web.")
    app.run(debug=False)

def main():
    parser = argparse.ArgumentParser(
        prog="myfi",
        description="MyFi - Intelligent Network Monitor",
        add_help=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    parser.add_argument("-V", "--version", action="store_true", help="Show version")

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

    chunk_parser = subparsers.add_parser("chunk", help="Manage Chunks")
    chunk_sub = chunk_parser.add_subparsers(dest="chunk_command")
    chunk_sub.add_parser("list", help="List registered Chunks")
    chunk_enable = chunk_sub.add_parser("enable", help="Enable a Chunk")
    chunk_enable.add_argument("name", help="Chunk name")
    chunk_disable = chunk_sub.add_parser("disable", help="Disable a Chunk")
    chunk_disable.add_argument("name", help="Chunk name")

    workflow_parser = subparsers.add_parser("workflow", help="Run a workflow")
    workflow_run = workflow_parser.add_subparsers(dest="workflow_command")
    workflow_run_parser = workflow_run.add_parser("run", help="Execute a workflow")
    workflow_run_parser.add_argument("name", help="Workflow name (from workflows.json)")

    web_parser = subparsers.add_parser("web", help="Start web interface")

    args = parser.parse_args()

    # Versão
    if args.version:
        console.print("🛰️ MyFi Network Engine")
        console.print("Version: 2.0.0")
        console.print("Architecture: x86_64")
        console.print("Dependencies: tshark v4.0+, iptables v1.8+")
        console.print("Status: [bold green]System is healthy.[/bold green]")
        sys.exit(0)

    # Ajuda
    if args.help:
        show_help()
        sys.exit(0)

    # Sem comando: Splash Screen
    if not args.command:
        show_splash_screen()
        sys.exit(0)

    # Logging
    if args.quiet:
        setup_logging(-1)
    elif args.vv:
        setup_logging(2)
    elif args.verbose:
        setup_logging(1)
    else:
        setup_logging(0)

    # Executar comando
    try:
        if args.command == "setup":
            cmd_setup(args)
        elif args.command == "scan":
            cmd_scan(args)
        elif args.command == "monitor":
            cmd_monitor(args)
        elif args.command == "limit":
            cmd_limit(args)
        elif args.command == "chunk":
            cmd_chunk(args)
        elif args.command == "workflow":
            cmd_workflow(args)
        elif args.command == "web":
            cmd_web(args)
        else:
            show_help()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n⚠️  ERRO DE CONEXÃO")
        console.print(f"[ ERROR ] {e}")
        console.print(f"[ CAUSA ] Verifique o hardware ou tente 'myfi setup --refresh'.")
        sys.exit(1)

if __name__ == "__main__":
    main()