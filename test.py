import socket
import subprocess

resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
linhas = resultado.stdout.split('\n')

dispositivos = []

for linha in linhas:
    if not linha.split():
        continue
    partes = linha.split()
    try:
        Nome = partes[0]
        IP = socket.gethostbyaddr(partes[1].strip('()'))
        MAC = partes[3]
        Interface = partes[6]
        dispositivos.append({'Nome': Nome, 'IP': IP, 'MAC': MAC, 'Interface': Interface})
    except IndexError:
        # Ignora linhas que não estão no formato esperado
        continue

for d in dispositivos:
    print(f"Nome: {d['Nome']}\nIP: {d['IP']}\nMAC: {d['MAC']}\nInterface: {d['Interface']}")
    print('-'*20)
	
