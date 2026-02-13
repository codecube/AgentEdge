#!/bin/bash
# Setup script for Jetson Orin Nano (Site A)
set -e

echo "=== Agent Edge - Jetson Setup ==="

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r agents/jetson/requirements.txt

# Create data directory
mkdir -p data

echo ""
echo "=== Setup Complete ==="
echo "Configure environment:"
echo "  export MACMINI_AGENT_URL=http://<macmini-ip>:8081"
echo "  export SERIAL_PORT=/dev/ttyUSB0"
echo ""
echo "Run agent:"
echo "  source .venv/bin/activate"
echo "  python -m agents.jetson.agent"
