#!/bin/bash
# Run Local Development Environment
# Starts Backend (Port 8000) and Frontend (Port 5173)

# Ensure Virtual Env
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python Virtual Environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "📦 Installing Backend Dependencies..."
    pip install fastapi uvicorn[standard] pyserial rpi_ws281x adafruit-circuitpython-neopixel RPi.GPIO
else
    source .venv/bin/activate
fi

cleanup() {
  echo "Stopping services..."
  kill $PID_BACKEND
  kill $PID_FRONTEND
}
trap cleanup EXIT

echo "🚀 Starting Backend (Emulation Mode)..."
export PYTHONPATH=$PYTHONPATH:.
python src/backend/server.py &
PID_BACKEND=$!

echo "🚀 Starting Frontend (Vite)..."
cd src/frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Frontend Dependencies..."
    npm install
fi
npm run dev &
PID_FRONTEND=$!

wait
