# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/lioexp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 📖 Read this in [Portuguese](README.pt.md)

**MyFi** is a modular observability and automation platform for small local networks.
It focuses on device visibility, traffic monitoring, and real-time alerts — with an extensible architecture built around **Chunks**.

---

## ✨ Features

* Automatic network interface detection and setup
* Local network device discovery (IP, MAC, interface)
* Per-device traffic monitoring
* Usage limits with real-time Telegram alerts
* Persistent storage using SQLite
* Clean CLI with verbosity levels

---

## 📦 Installation

```bash
git clone https://github.com/lioexp/myfi.git
cd myfi

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

---

## 🚀 Usage

### 1. Initial setup

```bash
python main.py setup
```

* Select your network interface
* Validate environment
* Save configuration

---

### 2. Scan your network

```bash
python main.py
```

![MyFi scanner](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

---

### 3. Enable alerts

Configure your Telegram token and chat ID in:

```
config/config.json
```

MyFi will notify you when a device exceeds its usage limit.

---

## 🗺️ Roadmap

* ✅ v0.5 – Setup wizard
* ✅ v1.0 – Network scanner
* ✅ v2.0 – Traffic monitoring & alerts
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

Built as part of a hands-on journey into networking and security.
