# InfraScope Architecture

## Overview

InfraScope follows a modular collector-analyzer-reporter architecture:

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│  Collectors  │───▶│  Analyzers   │───▶│   Reporters   │
│  (hardware   │    │  (scoring,   │    │  (terminal,   │
│   detection) │    │   analysis)  │    │   markdown…)  │
└─────────────┘    └──────────────┘    └───────────────┘
```

## Modules

### Core (`src/infrascope/core/`)
- `config.py` — Configuration management (JSON-based)
- `exceptions.py` — Custom exception hierarchy
- `dependency.py` — System dependency checking

### Collectors (`src/infrascope/collectors/`)
Each collector extends `BaseCollector` and implements `collect()`:
- `cpu.py` — CPU information, flags, caches, topology
- `memory.py` — RAM, DIMMs, NUMA, huge pages
- `gpu.py` — GPU detection (NVIDIA, AMD, Intel)
- `storage.py` — Disks, SMART, NVMe, LVM, RAID
- `network.py` — Interfaces, speed, offload, routing
- `motherboard.py` — Board info, BIOS, TPM, Secure Boot
- `cooling.py` — Temperatures, fans, thermal zones
- `power.py` — Power supplies, batteries, governors
- `usb.py` — USB device tree
- `pci.py` — PCI device classification
- `monitors.py` — Display/EDID information
- `audio.py` — Audio devices and codecs
- `virtualization.py` — VM/container detection
- `filesystem.py` — Mounts, fstab, tmpfs, overlay

### Analyzers (`src/infrascope/analyzers/`)
- `benchmark.py` — CPU/memory/storage benchmarks
- `scoring.py` — Component and overall scoring (0-100)
- `bottlenecks.py` — Automated bottleneck detection
- `upgrades.py` — Upgrade recommendations with estimates
- `workloads.py` — Workload capability assessment
- `comparisons.py` — Tier-based hardware comparison

### Reporting (`src/infrascope/reporting/`)
- `terminal.py` — Rich-based terminal output
- `markdown.py` — Markdown report generation
- `json_report.py` — JSON export
- `html_report.py` — HTML report with styling
- `csv_report.py` — CSV data export

## Data Flow

1. CLI command invoked → Typer routes to function
2. Collectors run hardware detection → `CollectorResult`
3. Analyzers process results → Scores, bottlenecks, etc.
4. Reporters format output → Terminal/file
