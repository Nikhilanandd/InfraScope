#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        InfraScope Installer              ║"
echo "  ║  Advanced Linux Hardware Analyzer        ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python version
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}Error: Python 3 not found. Please install Python 3.12+${NC}"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PY_VERSION detected"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install with uv (preferred)
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} uv package manager detected"
    echo ""
    echo -e "${CYAN}Installing InfraScope with uv...${NC}"
    uv tool install --force .
    echo ""
    echo -e "${GREEN}✓${NC} InfraScope installed globally with uv"

    echo ""
    echo -e "${CYAN}For development, use instead:${NC}"
    echo "  cd $SCRIPT_DIR && uv sync"

# Fallback to pip
elif command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}uv not found, using pip3 instead${NC}"
    echo -e "${CYAN}Installing with pip...${NC}"
    pip3 install -e .
    echo -e "${GREEN}✓${NC} InfraScope installed with pip"
elif command -v pip &> /dev/null; then
    echo -e "${YELLOW}uv not found, using pip instead${NC}"
    echo -e "${CYAN}Installing with pip...${NC}"
    pip install -e .
    echo -e "${GREEN}✓${NC} InfraScope installed with pip"
else
    echo -e "${RED}Error: No Python package manager found (uv, pip3, pip)${NC}"
    exit 1
fi

# Suggest installing system dependencies
echo ""
echo -e "${YELLOW}Recommended system packages (for full hardware detection):${NC}"
echo ""
if command -v apt-get &> /dev/null; then
    echo "  sudo apt-get install -y dmidecode smartmontools lshw pciutils usbutils \\"
    echo "    hwinfo nvme-cli iproute2 ethtool fio lm-sensors inxi"
elif command -v dnf &> /dev/null; then
    echo "  sudo dnf install -y dmidecode smartmontools lshw pciutils usbutils \\"
    echo "    hwinfo nvme-cli iproute ethtool fio lm_sensors inxi"
elif command -v pacman &> /dev/null; then
    echo "  sudo pacman -S dmidecode smartmontools lshw pciutils usbutils \\"
    echo "    hwinfo nvme-cli iproute2 ethtool fio lm_sensors inxi"
elif command -v zypper &> /dev/null; then
    echo "  sudo zypper install dmidecode smartmontools lshw pciutils usbutils \\"
    echo "    hwinfo nvme-cli iproute2 ethtool fio lm-sensors inxi"
fi

echo ""
echo -e "${CYAN}${BOLD}Usage:${NC}"
echo "  infrascope scan       # Quick hardware scan"
echo "  infrascope full       # Full system analysis"
echo "  infrascope cpu        # CPU information"
echo "  infrascope ram        # Memory information"
echo "  infrascope gpu        # GPU information"
echo "  infrascope help       # Show all commands"
echo ""
echo -e "${GREEN}Installation complete!${NC}"
