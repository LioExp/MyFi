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

### Se estiver no diretório `backend`:

```bash
python Scanner.py
```

### Se estiver na raiz do projeto:

```bash
python backend/Scanner.py
```

---

## 📡 Saída

O script irá mostrar:

* Todos os dispositivos que o seu computador **está conectado ou já se conectou**
* Informações como:

  * Nome
  * IP
  * MAC
  * Interface

Além disso, os dados são guardados automaticamente em um ficheiro de log.

