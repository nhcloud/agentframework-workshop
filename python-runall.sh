#!/bin/bash
# Launch Python Backend and Frontend together
# This script starts both the Python backend API and the React frontend

echo "========================================"
echo "Starting Python Agent Framework Workshop"
echo "========================================"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start the Python backend in the background (with .venv activated)
echo "Starting Python Backend..."
cd "$SCRIPT_DIR/Backend/python"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

# Wait a moment for the backend to initialize
sleep 3

# Start the frontend in the background
echo "Starting Frontend..."
cd "$SCRIPT_DIR/frontend"
npm start &
FRONTEND_PID=$!

echo "========================================"
echo "Both services are starting..."
echo "- Backend: http://localhost:8000 (or configured port)"
echo "- Frontend: http://localhost:3001"
echo "========================================"
echo "Press Ctrl+C to stop both services."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
