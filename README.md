# InfraScope

**Advanced Linux System Hardware & Performance Analyzer**

InfraScope is a production-grade CLI tool that performs comprehensive hardware detection, benchmarking, bottleneck analysis, upgrade recommendations, and workload capability assessment for Linux systems.

## Features

- **Hardware Discovery** — Detect every component: CPU, RAM, GPU, storage, network, motherboard, USB, PCI, cooling, and more
- **Benchmark Engine** — Measure CPU, memory, and storage performance
- **Performance Scoring** — Generate component and overall system scores (0-100)
- **Bottleneck Detection** — Automatically identify CPU, GPU, RAM, disk, PCIe, thermal, network, and power bottlenecks
- **Upgrade Advisor** — Get actionable upgrade recommendations with estimated improvements
- **Workload Assessment** — Evaluate capability for 25+ workloads (Docker, Kubernetes, ML, LLMs, gaming, etc.)
- **Comparison** — Compare hardware against Entry, Mid, High, Professional, and Enterprise tiers
- **Multiple Reports** — Terminal (Rich), Markdown, JSON, HTML, CSV, PDF
- **Live Monitoring** — Real-time system monitoring dashboard
- **Doctor Mode** — Diagnose and fix common issues

## Quick Start

```bash
# Install from source with uv (recommended)
git clone <repo-url>
cd infrascope
uv tool install --force .
infrascope scan

# Or use the install script (auto-detects uv/pip)
./install.sh

# Or for development (editable install with venv)
uv sync
source .venv/bin/activate
infrascope scan

# Run a quick scan
infrascope scan

# Full system analysis
infrascope full

# Generate HTML report
infrascope report --html
```

## Commands

| Command | Description |
|---------|-------------|
| `scan` | Quick hardware scan |
| `full` | Complete system analysis |
| `cpu` | CPU information |
| `ram` | Memory information |
| `gpu` | GPU information |
| `storage` | Storage information |
| `network` | Network information |
| `benchmark` | Run performance benchmarks |
| `compare` | Compare against standard tiers |
| `health` | System health overview |
| `temperatures` | Temperature and cooling |
| `bottlenecks` | Detect bottlenecks |
| `upgrades` | Upgrade recommendations |
| `workloads` | Workload capability assessment |
| `score` | Performance scores |
| `summary` | Brief system summary |
| `monitor --live` | Live monitoring dashboard |
| `topology` | System topology diagram |
| `inventory` | Hardware inventory |
| `doctor --fix` | Diagnose and fix issues |
| `report --html` | Generate HTML report |
| `report --json` | Generate JSON report |
| `report --md` | Generate Markdown report |
| `report --csv` | Generate CSV report |
| `export json` | Export system data |
| `deps` | Check dependencies |
| `version` | Show version |

## Examples

```bash
# Full system analysis
infrascope full

# Check what workloads your system can handle
infrascope workloads

# Get upgrade recommendations
infrascope upgrades

# Generate a beautiful HTML report
infrascope report --html

# Monitor system in real-time
infrascope monitor --live

# Detect bottlenecks
infrascope bottlenecks

# Run benchmarks
infrascope benchmark

# Diagnose and fix
infrascope doctor --fix
```

## Requirements

- Python 3.12+
- Linux (Ubuntu, Debian, Fedora, RHEL, Arch, etc.)

### Optional System Dependencies

For full hardware detection:

```bash
# Debian/Ubuntu
sudo apt-get install dmidecode smartmontools lshw pciutils usbutils hwinfo nvme-cli iproute2 ethtool fio lm-sensors inxi

# Fedora/RHEL
sudo dnf install dmidecode smartmontools lshw pciutils usbutils hwinfo nvme-cli iproute ethtool fio lm_sensors inxi

# Arch
sudo pacman -S dmidecode smartmontools lshw pciutils usbutils hwinfo nvme-cli iproute2 ethtool fio lm_sensors inxi
```

## Architecture

```
src/infrascope/
├── main.py              # CLI entry point
├── core/                # Config, exceptions, dependencies
├── collectors/          # Hardware detection modules
│   ├── cpu.py
│   ├── memory.py
│   ├── gpu.py
│   ├── storage.py
│   ├── network.py
│   └── ...
├── analyzers/           # Analysis modules
│   ├── benchmark.py
│   ├── scoring.py
│   ├── bottlenecks.py
│   ├── upgrades.py
│   └── workloads.py
├── reporting/           # Report generators
│   ├── terminal.py
│   ├── markdown.py
│   ├── json_report.py
│   ├── html_report.py
│   └── csv_report.py
└── utils/               # Utilities
```

## License

[GNU General Public License v3.0 (GPLv3)](LICENSE)
