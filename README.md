# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/lioexp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 📖 Read this in [Portuguese](README.pt.md)

**MyFi** is a modular observability and automation platform for small local networks.  
It discovers devices, monitors traffic, enforces usage limits, and sends real‑time alerts — with an extensible architecture built around **Chunks**.

---

## ✨ Features

* Interactive setup wizard (interface detection, device type, Telegram credentials)
* Local network device discovery (IP, MAC, interface)
* Per‑device traffic monitoring (live or low‑power modes)
* Configurable usage limits with Telegram alerts
* Limit management via CLI (`myfi limit set/show/remove`)
* SQLite persistence for devices, traffic logs, and limits
* Clean CLI with verbosity levels (`-q`, `-v`, `-vv`)

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

The wizard will ask you:
* Which kind of device you are using (local PC, hotspot, router)
* Network interface to monitor
* Telegram bot credentials (optional)

### 2. Scan your network

```bash
python main.py
```

![MyFi scanner](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

### 3. Start traffic monitoring

```bash
myfi monitor start            # low‑power mode (5 min interval)
myfi monitor start --live     # real‑time (2 s capture window)
myfi monitor stop
myfi monitor report
```

### 4. Manage usage limits

```bash
myfi limit set --mac aa:bb:cc:dd:ee:ff --daily 200
myfi limit show
myfi limit remove --mac aa:bb:cc:dd:ee:ff
```

When a device reaches 80 % of its limit, MyFi sends a Telegram warning; at 100 % it sends a critical alert and stops the device.

---

## 🗺️ Roadmap

* ✅ v0.5 – Setup wizard
* ✅ v1.0 – Network scanner
* ✅ v2.0 – Traffic monitoring, limits, and alerts
* ⏳ v3.0 – Chunk system (modular automation)
* ⏳ v4.0 – AI anomaly detection
* ⏳ v5.0 – Graphical interface

---

## 🤝 Contributing

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 📄 License

MIT © [LioExp](https://github.com/lioexp)

---

## 🙌 Notes

Built as part of a hands‑on journey into networking and security.
