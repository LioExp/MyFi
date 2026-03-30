#oxe?
import subprocess

resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
linhas = resultado.stdout.split("\n")

# uma lista pra armazenar todos os dispositivos que o pc se conecotou ou tentou se conectar(lá ele)
dispositivos = []

for linha in linhas :
	if not linha.strip():
		continue
	partes = linha.split()
	
	Nome = partes[0]
	IP = partes[1].strip('()')
	MAC = partes[3]
	Interface = partes[6]
	dispositivos.append({'Nome': Nome,'IP': IP,'MAC': MAC,'Interface': Interface})

# aqui ele roda pra todos os dispositivos que estiverem guardados no dicionário
for d in dispositivos:
	print(f"Nome: {d['Nome']}\nIP: {d['IP']}\nMAC: {d['MAC']}\nInterface: {d['Interface']}")
	print('-'*20)
