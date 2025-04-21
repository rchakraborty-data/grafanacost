#!/bin/bash

# run_app.sh - Script to start the Grafana Cost Dashboard application

# Ensure we're using the virtual environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment
source $VENV_DIR/bin/activate

# Install dependencies if needed
pip install -r requirements.txt

# Start the application
echo "Starting Grafana Cost Dashboard application..."
python3 app.py

# The script will not reach this point unless the application is stopped
echo "Application has been stopped."