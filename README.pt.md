# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/lioexp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 📖 Leia em [English](README.md)

**MyFi** é uma plataforma modular de observabilidade e automação para redes locais de pequena escala.
Foca em visibilidade de dispositivos, monitorização de tráfego e alertas em tempo real — com uma arquitetura extensível baseada em **Chunks**.

---

## ✨ Funcionalidades

* Deteção automática de interfaces de rede
* Descoberta de dispositivos na rede local (IP, MAC, interface)
* Monitorização de tráfego por dispositivo
* Limites de consumo com alertas via Telegram
* Armazenamento persistente com SQLite
* CLI limpa com níveis de verbosidade

---

## 📦 Instalação

```bash id="tq3zqg"
git clone https://github.com/lioexp/myfi.git
cd myfi

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

---

## 🚀 Uso

### 1. Configuração inicial

```bash id="x3m9bq"
python main.py setup
```

* Seleciona a interface de rede
* Valida o ambiente
* Guarda a configuração

---

### 2. Executar o scanner

```bash id="n9k2ds"
python main.py
```

![MyFi scanner](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

---

### 3. Ativar alertas

Configura o token e chat ID do Telegram em:

```id="6y7r2w"
config/config.json
```

O MyFi envia alertas quando um dispositivo atinge o limite definido.

---

## 🗺️ Roadmap

* ✅ v0.5 – Assistente de configuração
* ✅ v1.0 – Scanner de rede
* ✅ v2.0 – Monitorização e alertas
* ⏳ v3.0 – Sistema de Chunks (automação modular)
* ⏳ v4.0 – Deteção de anomalias com IA
* ⏳ v5.0 – Interface gráfica

---

## 🤝 Contribuição

Contribuições são bem-vindas. Consulte [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 📄 Licença

MIT © [LioExp](https://github.com/lioexp)

---

## 🙌 Nota

Projeto desenvolvido como parte de uma jornada prática em redes e segurança.
