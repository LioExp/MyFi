# 🛰️ MyFi

<img width="800" height="343" alt="image" src="https://github.com/user-attachments/assets/fd98e5ca-075a-482c-846e-ba78295e42a2" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/lioexp/myfi/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 📖 Read this in [Portuguese](README.pt.md).

**MyFi** is a modular observability and automation platform for small-scale local networks.
It provides device discovery, traffic monitoring, usage limits, Telegram alerts, and an extensible architecture through **Chunks**.

---

## ✨ Features

### v0.5 – Setup Wizard

* Automatic detection of active network interfaces (e.g., `wlan0`, `eth0`)
* Optional dependency checks (`tshark`, `iptables`)
* Traffic capture test
* Saves configuration to `~/.myfi/config.json`

### v1.0 – Network Scanner

* Lists devices on the local network using `arp -a`
* Displays **Name**, **IP**, **MAC**, and **Interface** in a colored table using `rich`
* Automatically logs results to a SQLite database with timestamps
* Integrated with the setup wizard (uses the configured interface)

### v2.0 – Traffic Monitoring & Alerts

* Measures per-device traffic (bytes sent/received) at regular intervals
* Allows setting usage limits in the configuration file
* Sends Telegram alerts when a device reaches its limit
* SQLite database to store device history
* CLI with verbosity levels (`-q`, `-v`, `-vv`)
* Traffic capture via `tshark` (optional)

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/lioexp/myfi.git
cd myfi

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

**Main dependencies:**

* `rich` – colored terminal formatting
* `requests` – for Telegram alerts
* `tshark` (optional) – for detailed traffic capture
* standard libraries: `subprocess`, `socket`, `json`, `sqlite3`

---

## 🚀 Usage

### 1. Setup MyFi (first run)

```bash
python main.py setup
```

The wizard will:

* List active network interfaces
* Ask you to select the interface connected to your network
* Check dependencies
* Save configuration to `~/.myfi/config.json`

---

### 2. Run the network scanner

```bash
python main.py
```

**Example output (CLI with `rich`):**

![MyFi scanner table](https://github.com/user-attachments/assets/6eaf6b9a-0219-422a-91fc-2da4ce382cc1)

Results are also saved to (`logs/scan.txt`).

---

### 3. Telegram Alerts (if configured)

If you set a token and chat ID in `config/config.json`, MyFi will send alerts when a device reaches the usage limit defined in that file.

---

## 📁 Project Structure

```
myfi/                  # Root folder
├── src/
│   └── myfi/          # Python package
│       ├── core/      # Business logic
│       │   ├── config_manager.py
│       │   ├── scanner.py
│       │   ├── monitor.py
│       ├── ui/
│       │   └── cli/
│       │       └── setup_wizard.py
│       ├── db/        # Database layer
│       └── data/      # SQLite (myfi.db)
├── config/            # Sensitive configs (e.g., Telegram token)
├── logs/              # Log files
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

* ✅ **v0.5** – Setup wizard
* ✅ **v1.0** – ARP scanner with rich, reverse DNS, logging, GitHub
* ✅ **v2.0** – Traffic monitor, limits, Telegram alerts, SQLite, verbosity
* ⏳ **v3.0** – Chunk system (modular automation)
* ⏳ **v4.0** – AI-based anomaly detection (Isolation Forest)
* ⏳ **v5.0** – Graphical interface (web app or desktop)

---

## 🤝 Contributing

Contributions are welcome! Check the [CONTRIBUTING.md](./CONTRIBUTING.md) file and follow semantic commit standards.

---

## 📄 License

MIT © [LioExp](https://github.com/lioexp)

---

## 🙌 Acknowledgments

This project was developed as part of a learning journey in networking and security, with a focus on autonomy.

