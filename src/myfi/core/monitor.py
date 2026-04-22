import subprocess
import socket
import time
import sys
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich import box
from src.myfi.core.config_manager import load_config
from src.myfi.core.Scanner import reverse_dns
from src.myfi.db.database import save_to_db
from src.myfi.core.alert_telegram import send_telegram_message
from config.config import TOKEN, CHAT_ID

console = Console()

def get_local_ip(): 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def get_own_mac(ip_address):

    try:
        resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        for linha in resultado.stdout.splitlines():
            partes = linha.split()
            if len(partes) >= 4 and partes[1].strip('()') == ip_address:
                return partes[3]
    except Exception:
        pass
    return "Unknown"


def capture_traffic(interface, my_ip, duration=10):
    # Bytes recebidos (ip.dst == meu_ip)
    cmd_received = [
        'sudo', 'tshark', '-i', interface,
        '-a', f'duration:{duration}',
        '-T', 'fields', '-e', 'frame.len',
        '-Y', f'ip.dst == {my_ip}'
    ]
    res_recv = subprocess.run(cmd_received, capture_output=True, text=True)
    # Bytes enviados (ip.src == meu_ip)
    cmd_sent = [
        'sudo', 'tshark', '-i', interface,
        '-a', f'duration:{duration}',
        '-T', 'fields', '-e', 'frame.len',
        '-Y', f'ip.src == {my_ip}'
    ]
    res_sent = subprocess.run(cmd_sent, capture_output=True, text=True)
    
    bytes_recv = sum(int(linha.strip()) for linha in res_recv.stdout.splitlines() if linha.strip().isdigit())
    bytes_sent = sum(int(linha.strip()) for linha in res_sent.stdout.splitlines() if linha.strip().isdigit())
    
    return bytes_recv, bytes_sent


def format_bytes(num_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"

def run_monitor(interface= None, threshold_mb=1):
    if interface is None:
        config = load_config()
        interface = config.get('interface', 'wlan0')

    # Configurações
    threshold_bytes = threshold_mb * 1024 * 1024
    alert_sent = False
    
    my_ip = get_local_ip()
    my_mac = get_own_mac(my_ip)
    hostname = reverse_dns(my_ip)
    
    total_recv = 0
    total_sent = 0
    cycle_count = 0
    
    console.clear()
    console.print("[bold cyan]MyFi - Live Network Monitor[/bold cyan]")
    console.print(f"Interface: {interface} | Local IP: {my_ip} | MAC: {my_mac}", style="dim")
    console.print("─" * 50, style="dim")
    console.print("Press [bold]Ctrl+C[/bold] to stop monitoring.\n")
    
    def generate_layout():
        total = total_recv + total_sent
        progress_percent = min(total / threshold_bytes, 1.0) if threshold_bytes > 0 else 0
        
        # Layout principal
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=8),
            Layout(name="footer", size=3)
        )
        
        # Cabeçalho
        header_text = Text()
        header_text.append("📡 Monitoring ", style="bold white")
        header_text.append(f"{interface}", style="bold cyan")
        header_text.append(f" • Cycle {cycle_count}", style="dim")
        layout["header"].update(Panel(header_text, box=box.MINIMAL, border_style="dim"))
        
        # Estatísticas
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column(style="bold white", width=15)
        stats_table.add_column(style="cyan")
        stats_table.add_column(style="bold white", width=15)
        stats_table.add_column(style="green")
        
        stats_table.add_row(
            "Download", format_bytes(total_recv),
            "Upload", format_bytes(total_sent)
        )
        stats_table.add_row(
            "Total", format_bytes(total),
            "Threshold", f"{threshold_mb} MB"
        )
        
        bar_length = 30
        filled = int(bar_length * progress_percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        if total >= threshold_bytes and threshold_bytes > 0:
            bar_color = "red"
        elif progress_percent > 0.8:
            bar_color = "yellow"
        else:
            bar_color = "green"
        bar_display = f"[{bar_color}]{bar}[/{bar_color}] {progress_percent*100:.1f}%"
        
        stats_panel = Panel(
            stats_table,
            title="Traffic Statistics",
            title_align="left",
            box=box.MINIMAL,
            border_style="dim"
        )
        layout["stats"].update(stats_panel)
        
        # Rodapé
        footer_text = Text()
        if total >= threshold_bytes:
            footer_text.append("⚠️  Threshold exceeded! Alert sent.", style="bold red")
        else:
            footer_text.append(f"Progress: {bar_display}", style="dim")
        footer_text.append("\n[dim]Updated every 10 seconds[/dim]")
        layout["footer"].update(Panel(footer_text, box=box.MINIMAL, border_style="dim"))
        
        return layout
    
    try:
        with Live(generate_layout(), refresh_per_second=4, screen=False) as live:
            while True:
                # Captura tráfego por 10 segundos
                recv, sent = capture_traffic(interface, my_ip, duration=10)
                total_recv += recv
                total_sent += sent
                cycle_count += 1
                
                # Salva no banco de dados
                try:
                    save_to_db(my_mac, hostname, my_ip, total_sent, total_recv)
                except Exception as e:
                    pass
                
                # Verifica limite e envia alerta Telegram
                total = total_recv + total_sent
                if total >= threshold_bytes and not alert_sent:
                    message = (
                        f"⚠️ MyFi Alert!\n"
                        f"Device {hostname} ({my_ip}) has exceeded the {threshold_mb} MB limit.\n"
                        f"Total traffic: {format_bytes(total)}"
                    )
                    try:
                        send_telegram_message(TOKEN, CHAT_ID, message=message)
                        alert_sent = True
                    except Exception:
                        pass
                
                live.update(generate_layout())
                
    except KeyboardInterrupt:
        console.print("\n[green]✓ Monitoring stopped.[/green]")
        console.print(f"Final stats: ↓ {format_bytes(total_recv)}  ↑ {format_bytes(total_sent)}")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)

def main():
    """Entrada quando chamado via 'myfi monitor'."""
    import argparse
    config = load_config()
    default_interface = config.get('interface', 'wlan0')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--interface', '-i', default=default_interface, help='Interface de rede')
    parser.add_argument('--threshold', '-t', type=int, default=1, help='Limite em MB para alerta')
    args, _ = parser.parse_known_args()
    
    run_monitor(interface=args.interface, threshold_mb=args.threshold)


if __name__ == "__main__":
    main()