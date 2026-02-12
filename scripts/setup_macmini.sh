#!/bin/bash
# Setup script for Mac Mini M2 (Control Center)
set -e

echo "=== Agent Edge - Mac Mini Setup ==="

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r agents/macmini/requirements.txt
pip install -r dashboard/requirements.txt

# Create data directory
mkdir -p data

echo ""
echo "=== Setup Complete ==="
echo "Configure environment:"
echo "  export JETSON_AGENT_URL=http://<jetson-ip>:8080"
echo ""
echo "Run agent:"
echo "  source .venv/bin/activate"
echo "  python -m agents.macmini.agent"
echo ""
echo "Run dashboard:"
echo "  streamlit run dashboard/app.py"
