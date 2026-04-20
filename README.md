# 🛰️ MyFi

MyFi é um monitor prático de redes para MiFi desenvolvido em Python.  
Descobre dispositivos conectados (IP, MAC), regista logs, controla banda e oferece automação modular (chunks).  

Inclui:
- Soft delete  
- Deteção de duplicatas por hash  
- Planeamento de integração com IA para deteção de anomalias  

Projeto open-source focado em **gestão e segurança de redes locais**.

---

## 🚧 Estado Atual do Projeto

Atualmente, o MyFi encontra-se na versão **v1.0 (em desenvolvimento)**.

### Funcionalidades atuais:
- Scanner de rede baseado em `arp -a`
- Listagem de dispositivos:
  - Nome
  - IP
  - MAC
  - Interface
- Logging automático em ficheiro (`scan.txt`)
- Timestamp de cada scan

---

## ⚙️ Instalação

1. Clonar o repositório:
```bash
git clone <repo-url>
````

2. Entrar no diretório do projeto:

```bash
cd MyFi
```

3. (Opcional) Instalar dependências:

```bash
pip install -r requirements.txt
```

> Nota: A maioria das bibliotecas utilizadas já vem incluída no Python.

---

## ▶️ Como Executar

### Dentro da raiz do projeto:

```bash
python main.py
```

---

## 📡 Saída

O script irá mostrar:

<img width="378" height="205" alt="image" src="https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1" />

