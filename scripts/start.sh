#!/bin/bash
# Run Production Environment (Pi)
# Starts Backend Only (Frontend is assumed to be built and served by Nginx)

# Activate Virtual Env
source .venv/bin/activate

echo "🚁 Starting Beatha Backend..."
export PYTHONPATH=$PYTHONPATH:.
# Run with uvicorn directly for better performance or just the script
python src/backend/server.py
