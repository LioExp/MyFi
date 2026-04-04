import subprocess
from datetime import datetime
import socket
from rich.console import Console
from rich.table import Table

# Executa o comando arp -a e captura o output armazenando na variavel 'resultado'
resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
linhas = resultado.stdout.split("\n")

# Lista para armazenar todos os dispositivos que o teu pc ou sla qual dispositivo que vc esteja usando  se conectou ou tentou se conectar(lá ele)
dispositivos = []

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def reverse_dns(ip_address):
    try:
        # Returns (hostname, alias_list, ip_addr_list)
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror:
        return "Unknown host"

# criar o objecto console e a tabela
console = Console()
table = Table(title=f'Redes Disponíveis – {timestamp}', show_header=True, header_style='bold magenta')

# Adicionar colunas (com estilos e alinhamento)
table.add_column('Nome', justify='center', style='cyan',  no_wrap=True)
table.add_column('IP', style='white', justify='center')
table.add_column('MAC', justify='center', style='green',no_wrap=True)
table.add_column('Interface',justify='center', style='green' )


# Processa cada linha do resultado do arp 
for linha in linhas:
    if not linha.strip():
        continue
    partes = linha.split()

    try:
        Nome = partes[0]
        IP = partes[1].strip('()')
        MAC = partes[3]
        Interface = partes[6]
        dispositivos.append({'Nome': reverse_dns(IP), 'IP': IP, 'MAC': MAC, 'Interface': Interface})
    except IndexError:
        # Ignora linhas que não estão no formato esperado
        continue

# Salva os resultados no arquivo scan.txt
with open('logs/scan.txt', 'a') as test:
    test.write(f"\n=== Scan realizado em {timestamp} ===\n")	
    for d in dispositivos:
        test.write(f"""Nome: {d['Nome']}
        IP: {d['IP']}
        MAC: {d['MAC']}
        Interface: {d['Interface']}
        ------------------------
        """)

# agora printamos todos  os dispositivos  no terminal

for d in dispositivos:
    table.add_row(*d.values())
    console.print(table)

'''
for d in dispositivos:
    print(f"\n=== Scan realizado em {timestamp} ===\n")
    print(f"Nome: {d['Nome']}\nIP: {d['IP']}\nMAC: {d['MAC']}\nInterface: {d['Interface']}")
    print('-'*20)
'''
