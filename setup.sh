#!/bin/bash
# Setup script for PDF Anonymizer

echo "=== PDF Anonymizer Setup ==="
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Download spaCy English model (required by Presidio)
echo "Downloading spaCy English model..."
python -m spacy download en_core_web_lg

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use the anonymizer:"
echo "  1. Activate the environment: source venv/bin/activate"
echo "  2. Run: python anonymizer.py anonymize your_file.pdf output.txt"
echo ""
