#!/bin/bash
# Demo launcher - starts both agents and dashboard locally
# For development/testing on a single machine
set -e

echo "=== Agent Edge - Demo Launcher ==="

# Ensure virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

mkdir -p data

echo "[1/3] Starting Mac Mini Agent (port 8081)..."
python3 -m agents.macmini.server &
MACMINI_PID=$!
sleep 2

echo "[2/3] Starting Jetson Agent (port 8080)..."
python3 -m agents.jetson.server &
JETSON_PID=$!
sleep 2

echo "[3/3] Starting Dashboard..."
streamlit run dashboard/app.py &
DASH_PID=$!

echo ""
echo "=== All components running ==="
echo "  Jetson Agent:  http://localhost:8080 (PID: $JETSON_PID)"
echo "  Mac Mini Agent: http://localhost:8081 (PID: $MACMINI_PID)"
echo "  Dashboard:      http://localhost:8501 (PID: $DASH_PID)"
echo ""
echo "Press Ctrl+C to stop all components"

# Cleanup on exit
trap "kill $MACMINI_PID $JETSON_PID $DASH_PID 2>/dev/null; echo 'Stopped.'" EXIT

wait
