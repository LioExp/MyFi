import subprocess
import socket
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def reverse_dns(ip_address):
    #Tenta resolver o hostname reverso do IP
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror:
        return "Unknown"

def main():
    #Executa o scan da rede local via ARP e exibe os resultados
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with console.status("[bold cyan]Scanning local network...[/bold cyan]", spinner="dots"):
        resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
    
    if resultado.returncode != 0:
        console.print("[red]✗ Failed to run arp command.[/red]")
        return
    
    linhas = resultado.stdout.splitlines()
    dispositivos = []
    
    for linha in linhas:
        if not linha.strip():
            continue
        partes = linha.split()
        try:
            nome = partes[0]
            ip = partes[1].strip('()')
            mac = partes[3]
            interface = partes[6] if len(partes) > 6 else "N/A"
            
            # Resolve DNS apenas se necessário (pode ser lento)
            hostname = reverse_dns(ip)
            
            dispositivos.append({
                'Hostname': hostname,
                'IP': ip,
                'MAC': mac,
                'Interface': interface
            })
        except IndexError:
            continue
    
    if not dispositivos:
        console.print("[yellow]! No devices found in ARP table.[/yellow]")
        return
    
    # Cria tabela estilo Claude Code (limpa, sem bordas pesadas)
    table = Table(
        title=f"Network Scan – {timestamp}",
        title_style="bold white",
        box=None,               # sem bordas
        show_header=True,
        header_style="bold cyan",
        padding=(0, 2)
    )
    table.add_column("Hostname", style="cyan")
    table.add_column("IP", style="white")
    table.add_column("MAC", style="green")
    table.add_column("Interface", style="dim white")
    
    for d in dispositivos:
        table.add_row(d['Hostname'], d['IP'], d['MAC'], d['Interface'])
    
    console.print(table)
    console.print(f"[dim]Total devices: {len(dispositivos)}[/dim]")
    
    # Salva em arquivo de log
    try:
        with open('logs/scan.txt', 'a') as log:
            log.write(f"\n=== Scan {timestamp} ===\n")
            for d in dispositivos:
                log.write(f"{d['Hostname']} | {d['IP']} | {d['MAC']} | {d['Interface']}\n")
    except FileNotFoundError:
        # Cria diretório logs se não existir
        import os
        os.makedirs('logs', exist_ok=True)
        with open('logs/scan.txt', 'w') as log:
            log.write(f"=== Scan {timestamp} ===\n")
            for d in dispositivos:
                log.write(f"{d['Hostname']} | {d['IP']} | {d['MAC']} | {d['Interface']}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Scan interrupted.[/yellow]")