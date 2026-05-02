#!/usr/bin/env bash

echo "Stopping Transmuter servers..."

# Find and kill processes on ports 4300 and 8000
PIDS=$(lsof -t -i :4300 -i :8000)

if [ -n "$PIDS" ]; then
    echo "Killing processes: $PIDS"
    echo "$PIDS" | xargs kill -9
    echo "Servers stopped successfully."
else
    echo "No servers found running on ports 4300 or 8000."
fi
