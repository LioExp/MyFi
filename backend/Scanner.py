import subprocess
from datetime import datetime
import socket

# Executa o comando arp -a e captura o output armazenando na variavel 'resultado'
resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
linhas = resultado.stdout.split("\n")

# Lista para armazenar todos os dispositivos que o teu pc ou sla qual dispositivo que vc esteja usando  se conectou ou tentou se conectar(lá ele)
dispositivos = []

def reverse_dns(ip_address):
    try:
        # Returns (hostname, alias_list, ip_addr_list)
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror:
        return "Unknown host"


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


timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    print(f"\n=== Scan realizado em {timestamp} ===\n")
    print(f"Nome: {d['Nome']}\nIP: {d['IP']}\nMAC: {d['MAC']}\nInterface: {d['Interface']}")
    print('-'*20)
	
