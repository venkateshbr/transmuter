#!/usr/bin/env bash

# Stop existing servers first
./stop.sh

echo "Starting Transmuter Backend (Port 8000)..."
cd apps/api
nohup uv run uvicorn app.main:app --port 8000 > ../../backend.log 2>&1 &
cd ../..

echo "Starting Transmuter Frontend (Port 4300)..."
cd apps/web
nohup npm start -- --port 4300 > ../../frontend.log 2>&1 &
cd ../..

echo "Servers are starting in the background."
echo "Logs are being written to frontend.log and backend.log."
echo "You can view them by running:"
echo "  tail -f frontend.log backend.log"
