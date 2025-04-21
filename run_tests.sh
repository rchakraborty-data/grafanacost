#!/bin/bash

# run_tests.sh - Script to run end-to-end tests for Grafana Cost Dashboard

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

# Run the tests
echo "Running end-to-end tests..."
python3 -m unittest test_e2e.py

# Check if tests were successful
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed. Please check the logs above."
    exit 1
fi