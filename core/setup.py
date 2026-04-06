import subprocess
import rich

#resulado = subprocess.run(['ip','link','show'], capture_output=True, text=True)
#cmd = resulado.stdout.split('\n')
#linhas = resulado.stdout.splitlines()

def detectar_interfaces_up():
    resultado = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
    linhas = resultado.stdout.splitlines()
    
    interfaces_up = []
    
    for i, linha in enumerate(linhas):
        # Verifica se é uma linha de início de interface (começa com número e ':')
        if linha and linha[0].isdigit() and ':' in linha:
            # Verifica se a interface está UP
            if 'UP' in linha and ('state UP' in linha or '<' in linha and 'UP' in linha.split('<')[1].split('>')[0]):
                # Extrai o nome da interface (entre o número: e o primeiro espaço)
                partes = linha.split(':')
                if len(partes) >= 2:
                    nome = partes[1].strip().split()[0]
                    interfaces_up.append(nome)
    
    return interfaces_up

# Exemplo de uso
print(detectar_interfaces_up())




'''
def detect_interface():
    for linha in cmd:
        if not linha.strip():
            continue
    partes =  linha.split()
    up = partes.find('up')

    return up
'''