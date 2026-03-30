import subprocess

resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
linhas = resultado.stdout.split()
Nome_dispositivo = f'Nome: {linhas[0]} \n IP: {linhas[1]} \n MAC:{linhas[3]} \n Interface:{linhas[6]}'
print(linhas)
print('---'*9)
print(Nome_dispositivo)
