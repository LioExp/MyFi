<div align="center">

<img width="800" height="343" alt="MyFi" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />


[![Python 3.8+](https://img.shields.io/badge/Python_3.8+-0d0a15?style=for-the-badge&logo=python&logoColor=7F77DD)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version_2.0.0-0d0a15?style=for-the-badge&logoColor=7F77DD)](https://github.com/LioExp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/MIT-0d0a15?style=for-the-badge&logoColor=7F77DD)](https://opensource.org/licenses/MIT)
[![LioExp](https://img.shields.io/badge/LioExp-0d0a15?style=for-the-badge&logo=youtube&logoColor=7F77DD)](https://www.youtube.com/@lioexp1)

</div>


> read in [Portuguese](README.pt.md)

---

> *I discovered unknown devices on my network. I built this to solve the problem.*
<!-- > — **[Watch the episode on the channel →](https://www.youtube.com/@lioexp1)** -->

**MyFi** is a modular observability platform for small local networks. It discovers devices, monitors traffic, enforces usage limits, and sends real‑time alerts — with an extensible architecture based on **Chunks**.

---

## ✨ Features

```
  ┌─────────────────────────────────────────────────────────┐
  │  myfi v2.0.0                                            │
  │                                                         │
  │  ✓  Interactive setup wizard                            │
  │  ✓  Device discovery (IP, MAC, interface)               │
  │  ✓  Per‑device traffic monitoring                       │
  │  ✓  Configurable limits with Telegram alerts            │
  │  ✓  CLI with verbosity levels (-q, -v, -vv)             │
  │  ✓  SQLite persistence                                  │
  └─────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

```bash
git clone https://github.com/lioexp/myfi.git
cd myfi/ && make setup
myfi setup
```

---

## 🚀 Usage

### 1. Initial setup

```bash
python main.py setup
```

The wizard will ask:
- Device type (local PC, hotspot, router)
- Network interface to monitor
- Telegram bot credentials (optional)

### 2. Network scan

```bash
python main.py
```

### 3. Traffic monitoring

```bash
myfi monitor start            # low‑power mode (5 min interval)
myfi monitor start --live     # real‑time (2s window)
myfi monitor stop
myfi monitor report
```

### 4. Limit management

```bash
myfi limit set --mac aa:bb:cc:dd:ee:ff --daily 200
myfi limit show
myfi limit remove --mac aa:bb:cc:dd:ee:ff
```

> At 80% of the limit → Telegram alert. At 100% → critical alert + device blocked.

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

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

<div align="center">

`// build. break. document.` &nbsp;·&nbsp; *Col 3:23*
