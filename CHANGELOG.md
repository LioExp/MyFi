All notable changes to MyFi will be documented in this file.

## [2.0.0] – 2026-04-26

### Added

- **Traffic monitoring** with `tshark` (`myfi monitor start`, `--live` mode)
- **Usage limits** per device (`myfi limit set/show/remove`)
- **Telegram alerts** when a device reaches 80 % (warning) or 100 % (critical) of its limit
- **SQLite database** with tables for devices, traffic logs, limits, and alert history
- Verbosity flags (`-q`, `-v`, `-vv`) for the whole CLI
- Live visual feedback during monitoring (instant + session totals)
- Accumulated daily totals that survive monitor restarts
- Reliable IP detection from the configured network interface
- Direct MAC reading from `/sys/class/net/<interface>/address`
- Setup wizard now asks for **device type** (local PC / hotspot) and Telegram credentials
- Logging redirected to `logs/myfi.log` (terminal stays clean)

### Changed

- `MonitorCore` uses a single `tshark` command with `ip host` filter instead of two separate commands
- Timeouts tuned for live mode (2‑second capture window)
- `ConfigManager` became a class with caching and JSON‑error handling
- `AlertManager` now persists alerts via `Database`
- Scanner moved to its own class with `Rich` output in the CLI

### Fixed

- “Unknown” MAC caused by fragile ARP‑table lookup
- `FOREIGN KEY constraint` when saving traffic before the device record
- Monitor using wrong IP (now reads real IP from interface)
- Infinite sudo password prompts (removed `sudo` from `tshark` commands; permission check added)
- Logs no longer pollute the terminal

## [1.0.0] – 2026-04

### Added

- ARP network scanner (`myfi scan`) with `rich` table output
- Reverse DNS resolution
- Timestamped logging to `logs/scan.txt`
- First GitHub release

## [0.5.0] – 2026-04

### Added

- Setup wizard (`myfi setup`) with:
  - Network interface detection
  - Dependency checks (`tshark`, `iptables`)
  - Packet capture test
  - Telegram configuration (hidden input)
- Configuration saved to `~/.myfi/config.json`
