#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}${BOLD}Uninstalling InfraScope...${NC}"

# Prefer uv, fallback to pip
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} Using uv"
    uv tool uninstall infrascope 2>/dev/null || true
    rm -rf .venv uv.lock 2>/dev/null || true
elif command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Using pip3"
    pip3 uninstall infrascope -y 2>/dev/null || true
elif command -v pip &> /dev/null; then
    echo -e "${GREEN}✓${NC} Using pip"
    pip uninstall infrascope -y 2>/dev/null || true
fi

# Remove config
CONFIG_DIR="${HOME}/.config/infrascope"
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Remove configuration directory? (y/N)${NC}"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓${NC} Configuration removed"
    fi
fi

# Remove reports
REPORTS_DIR="${HOME}/infrascope/reports"
if [ -d "$REPORTS_DIR" ]; then
    echo -e "${YELLOW}Remove reports directory? (y/N)${NC}"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        rm -rf "$REPORTS_DIR"
        echo -e "${GREEN}✓${NC} Reports removed"
    fi
fi

echo -e "${GREEN}✓${NC} InfraScope uninstalled"
