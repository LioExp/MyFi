<div align="center">

<img width="800" height="343" alt="MyFi" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />


[![Python 3.8+](https://img.shields.io/badge/Python_3.8+-0d0a15?style=for-the-badge&logo=python&logoColor=7F77DD)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version_2.0.0-0d0a15?style=for-the-badge&logoColor=7F77DD)](https://github.com/LioExp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/MIT-0d0a15?style=for-the-badge&logoColor=7F77DD)](https://opensource.org/licenses/MIT)
[![LioExp](https://img.shields.io/badge/LioExp-0d0a15?style=for-the-badge&logo=youtube&logoColor=7F77DD)](https://www.youtube.com/@lioexp1)

</div>

> Leia em [English](README.md)
---

> *Descobri que havia dispositivos desconhecidos na minha rede. Construí isto para resolver o problema.*
<!-- > — **[Ver o episódio no canal →](https://www.youtube.com/@lioexp1)** -->

**MyFi** é uma plataforma modular de observabilidade para redes locais pequenas. Descobre dispositivos, monitoriza tráfego, aplica limites de utilização e envia alertas em tempo real — com uma arquitectura extensível baseada em **Chunks**.

---

## ✨ Funcionalidades

```
  ┌─────────────────────────────────────────────────────────┐
  │  myfi v2.0.0                                            │
  │                                                         │
  │  ✓  Wizard de setup interactivo                        │
  │  ✓  Descoberta de dispositivos (IP, MAC, interface)     │
  │  ✓  Monitorização de tráfego por dispositivo            │
  │  ✓  Limites configuráveis com alertas Telegram          │
  │  ✓  CLI com níveis de verbosidade (-q, -v, -vv)         │
  │  ✓  Persistência SQLite                                 │
  └─────────────────────────────────────────────────────────┘
```

---

## 📦 Instalação

```bash
git clone https://github.com/lioexp/myfi.git
cd myfi/ && make setup
myfi setup
```

---

## 🚀 Utilização

### 1. Setup inicial

```bash
python main.py setup
```

O wizard vai perguntar:
- Tipo de dispositivo (PC local, hotspot, router)
- Interface de rede a monitorizar
- Credenciais do bot Telegram (opcional)

### 2. Scan da rede

```bash
python main.py
```

### 3. Monitorização de tráfego

```bash
myfi monitor start            # modo low-power (intervalo de 5 min)
myfi monitor start --live     # tempo real (janela de 2s)
myfi monitor stop
myfi monitor report
```

### 4. Gestão de limites

```bash
myfi limit set --mac aa:bb:cc:dd:ee:ff --daily 200
myfi limit show
myfi limit remove --mac aa:bb:cc:dd:ee:ff
```

> A 80% do limite → alerta Telegram. A 100% → alerta crítico + dispositivo bloqueado.

---

## 🗺️ Roadmap

```
  v0.5  ██████████  ✅  Setup wizard
  v1.0  ██████████  ✅  Network scanner
  v2.0  ██████████  ✅  Traffic monitoring, limits, alerts
  v3.0  ░░░░░░░░░░  ⏳  Chunk system (modular automation)
  v4.0  ░░░░░░░░░░  ⏳  AI anomaly detection
  v5.0  ░░░░░░░░░░  ⏳  Graphical interface
```

---

## 🤝 Contributing

Contribuições são bem-vindas. Vê [CONTRIBUTING.md](./CONTRIBUTING.md).

---

<div align="center">

`// build. break. document.` &nbsp;·&nbsp; *Col 3:23*
