
# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/lioexp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 📖 Read this in [English](README.pt.md).

**MyFi** é uma plataforma modular de observabilidade e automação para redes locais de pequena escala.  
Fornece descoberta de dispositivos, monitorização de tráfego, limites de consumo, alertas via Telegram e uma arquitetura extensível através de **Chunks**.


---

## ✨ Funcionalidades implementadas

### v0.5 – Assistente de Configuração
- Deteção automática de interfaces de rede ativas (ex: `wlan0`, `eth0`)
- Verificação de dependências opcionais (`tshark`, `iptables`)
- Teste de captura de tráfego
- Guarda configuração em `~/.myfi/config.json`

### v1.0 – Scanner de Rede
- Lista dispositivos na rede local usando `arp -a`
- Mostra **Nome**, **IP**, **MAC** e **Interface** numa tabela colorida com `rich`
- Registo automático em base de dados SQLite com timestamp
- Integração com o assistente (usa a interface configurada)

### v2.0 – Monitorização de Tráfego e Alertas
- Mede o tráfego de dados por dispositivo (bytes enviados/recebidos) em intervalos regulares
- Permite definir limites de consumo no ficheiro de configuração
- Envia alertas via Telegram quando um dispositivo atinge o limite
- Base de dados SQLite para armazenar histórico de dispositivos
- CLI com níveis de verbosidade (`-q`, `-v`, `-vv`)
- Captura de tráfego com `tshark` (opcional)

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
- `requests` – para alertas Telegram
- `tshark` (opcional) – para captura de tráfego detalhada
- bibliotecas padrão: `subprocess`, `socket`, `json`, `sqlite3`

---

## 🚀 Como usar

### 1. Configurar o MyFi (primeira execução)

```bash
python main.py setup
```

O assistente irá:
- Listar as interfaces de rede ativas
- Pedir que escolha a interface ligada à sua rede
- Verificar dependências
- Guardar a configuração em `~/.myfi/config.json`

### 2. Executar o scanner de rede

```bash
python main.py
```

**Exemplo de saída (CLI com `rich`):**

![Tabela do scanner MyFi](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

Os resultados são também guardados em  (`logs/scan.txt`).

### 3. Alertas Telegram (se configurados)

Se definiu um token e chat ID no `config/config.json`, o MyFi envia alertas quando um dispositivo atinge o limite de consumo definido nesse ficheiro.

---

## 📁 Estrutura do projeto

```
myfi/                  # Pasta raiz do repositório
├── src/
│   └── myfi/                  # O pacote Python
│       ├── core/              # Lógica de negócio
│       │   ├── config_manager.py
│       │   ├── scanner.py
│       │   ├── monitor.py
│       ├── ui/
│       │   └── cli/
│       │       └── setup_wizard.py
│       ├── db/                # Base de dados
│       └── data/              # SQLite (myfi.db)
├── config/                    # Configurações sensíveis (ex: token Telegram)
├── logs/                      # Ficheiros de log
├── tests/
├── docs/
├── main.py
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```
---

## 🗺️ Roadmap

- ✅ **v0.5** – Wizard de configuração
- ✅ **v1.0** – Scanner ARP com rich, DNS reverso, logging, GitHub
- ✅ **v2.0** – Monitor de tráfego, limites, alertas Telegram, SQLite, verbosidade
- ⏳ **v3.0** – Sistema de Chunks (automação modular)
- ⏳ **v4.0** – Deteção de anomalias com IA (Isolation Forest)
- ⏳ **v5.0** – Interface gráfica (web app ou desktop)

---

## 🤝 Contribuição

Contribuições são bem-vindas! Consulte o ficheiro [CONTRIBUTING.md](./CONTRIBUTING.md) e siga os padrões de commit semântico.

---

## 📄 Licença

MIT © [LioExp](https://github.com/lioexp).

---

## 🙌 Agradecimentos

Projeto desenvolvido como parte da jornada de aprendizagem em redes e segurança, com foco em autonomia.
