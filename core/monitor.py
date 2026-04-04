import subprocess
import socket

# funções globais
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, this just picks the local interface
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.168.1.6'
    finally:
        s.close()
    return ip

meu_ip = get_local_ip() 
# origem do pacote, filtro pra bytes recebidos com o ip.dst
resultado1 = subprocess.run(['sudo','tshark', '-i', 'wlan0', '-c', '10', '-T', 'fields', '-e', 'ip.dst', '-e', 'frame.len', '-Y',f'ip.dst == {meu_ip}'], capture_output=True, text=True)
#origem do pacote, iltro para bytes enviados com o ip.src
resultado2 = subprocess.run(['sudo','tshark', '-i', 'wlan0', '-c', '10', '-T', 'fields', '-e', 'ip.dst', '-e', 'frame.len', '-Y',f'ip.src == {meu_ip}'], capture_output=True, text=True)


#variaveis globais
Total_bytes_enviado = 0
Total_bytes_recebido = 0
linhas1 = resultado1.stdout.split('\n')
linhas2 = resultado2.stdout.split('\n')
  

# soma todos os bytes recebidos
for linha1 in linhas1:
    if not linha1.strip():
        continue
    partes1 = linha1.split()

    try:
        Bytes = partes1[1]
        Total_bytes_recebido += int(Bytes)

    except IndexError:
        continue

# soma todos os bytes enviados
for linha2 in linhas2:
    if not linha2.strip():
        continue
    partes2 = linha2.split()

    try:
        Bytes2 = partes2[1]
        Total_bytes_enviado += int(Bytes2)

    except IndexError:
        continue

print(f'IP: {meu_ip}\nBytes recebidos: {Total_bytes_recebido}\nbytes enviado: {Total_bytes_enviado}')