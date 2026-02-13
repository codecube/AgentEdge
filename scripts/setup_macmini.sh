#!/bin/bash
# Setup script for Mac (Control Center)
set -e

echo "=== Agent Edge - Mac Setup ==="

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create data directory
mkdir -p data

echo ""
echo "=== Setup Complete ==="
echo "Configure environment:"
echo "  export OLLAMA_API_BASE=http://localhost:11434"
echo "  export JETSON_AGENT_URL=http://<jetson-ip>:8080"
echo ""
echo "Run agent:"
echo "  source .venv/bin/activate"
echo "  python3 -m agents.macmini.server"
echo ""
echo "Run dashboard:"
echo "  streamlit run dashboard/app.py"
