#!/bin/bash

# run_app.sh - Script to start the Grafana Cost Dashboard application

# Check for wkhtmltopdf installation (required for PDF generation)
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "wkhtmltopdf not found. This is required for PDF generation."
    echo "Installing wkhtmltopdf using Homebrew..."
    if command -v brew &> /dev/null; then
        brew install wkhtmltopdf
    else
        echo "Homebrew not found. Please install wkhtmltopdf manually:"
        echo "Visit: https://wkhtmltopdf.org/downloads.html"
        echo "Or install Homebrew first with: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "Then run: brew install wkhtmltopdf"
        echo ""
        echo "Continuing startup without PDF capability..."
    fi
fi

# Ensure we're using the virtual environment
VENV_DIR=".venv" # Use .venv instead of venv
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment
source $VENV_DIR/bin/activate # Activate .venv

# Install dependencies if needed
pip install -r requirements.txt

# Start the application
echo "Starting Grafana Cost Dashboard application..."
python3 app.py

# The script will not reach this point unless the application is stopped
echo "Application has been stopped."