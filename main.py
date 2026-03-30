import subprocess


resultado = subprocess.run(['arp', '-a'],capture_output = True,text = True)
print(resultado.stderr)