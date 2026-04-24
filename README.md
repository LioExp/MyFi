# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MyFi** é um monitor de redes inteligente focado em MiFi (roteadores portáteis) e redes locais.  
Desenvolvido em Python, fornece descoberta de dispositivos (IP, MAC, hostname), logging, e uma arquitetura modular para futuras funcionalidades como controle de banda, automação e deteção de anomalias com IA.

> ⚠️ **Estado atual:** v1.0 em desenvolvimento – scanner de rede funcional com interface CLI  (`rich`).

---

## ✨ Funcionalidades já implementadas

### v0.5 – Assistente de Configuração
- Deteção automática de interfaces de rede ativas (ex: `wlan0`, `eth0`)
- Verificação de dependências opcionais (`tshark`, `iptables`)
- Teste de captura de tráfego (para funcionalidades futuras)
- Guarda configuração em `~/.myfi/config.json`

### v1.0 – Scanner de Rede (parcial)
- Lista dispositivos na rede local usando `arp -a`
- Mostra **Nome**, **IP**, **MAC** e **Interface** numa tabela com `rich`
- Registo automático em `logs/scan.txt` com timestamp
- Integração com o assistente (usa a interface configurada)

---

## 📦 Instalação

```bash
# Clonar o repositório
git clone https://github.com/lioexp/myfi.git
cd myfi

# Criar e ativar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Instalar dependências
pip install -r requirements.txt
```

**Dependências principais:**
- `rich` – formatação colorida no terminal
- `requests` – para alertas Telegram (futuro)
- bibliotecas padrão: `subprocess`, `socket`, `json`, `sqlite3`

---

## 🚀 Como usar

### 1. Configurar o MyFi (primeira execução)

```bash
python main.py setup
```

O assistente irá:
- Listar as interfaces de rede ativas
- Pedir que escolha a interface ligada ao seu MiFi
- Verificar dependências (não obrigatórias para o scanner)
- Testar a captura de tráfego (se `tshark` estiver instalado)
- Guardar a configuração em `~/.myfi/config.json`

### 2. Executar o scanner de rede

```bash
python main.py 
```

**Exemplo de saída (CLI com `rich`):**

![Tabela do scanner MyFi](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

Os resultados são também guardados em `logs/myfi.db`.

---

## 📁 Estrutura do projeto

```
myfi/
├── core/
│   ├── config_manager.py   # leitura/escrita da configuração
│   ├── Scanner.py          # lógica do scanner de rede
│   └── ...                 # futuros módulos (monitor, chunks, IA)
├── ui/
│   └── cli/
│       └── setup_wizard.py # assistente de configuração
├── config/                 # configurações sensíveis (ex: token Telegram)
├── logs/                   # ficheiros de log (scan.txt)
├── data/                   # base de dados SQLite (futuro)
├── main.py                 # ponto de entrada (comandos: setup, scan)
├── requirements.txt
└── README.md
```

---

## 🗺️ Roadmap (versões futuras)

- **v1.0** (MVP) – scanner completo + logging + CLI 
- **v2.0** – monitorização de tráfego com `tshark`, limites por dispositivo, alertas (Telegram/email)
- **v3.0** – sistema de chunks (automação modular)
- **v4.0** – deteção de anomalias com IA (Isolation Forest)
- **v5.0** – interface gráfica (PySide6 ou web local)
---

## 🤝 Contribuição

Contribuições são bem-vindas! Consulte o ficheiro [CONTRIBUTING.md](./CONTRIBUTING.md) e siga os padrões de commit semântico.

---

## 📄 Licença

MIT © [LioExp](https://github.com/lioexp).

---
## 🙌 Agradecimentos

Projeto desenvolvido como parte da jornada de aprendizagem em redes e segurança, com foco em autonomia.

