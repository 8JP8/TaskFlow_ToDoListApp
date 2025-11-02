#!/bin/bash
# Azure Web App startup script for Python 3.11
# This script is executed by Azure when the app starts

echo "Starting Flask application..."

# Install dependencies
pip install -r requirements.txt

# Run the Flask app using Gunicorn for production
# Azure will set the PORT environment variable
gunicorn --bind 0.0.0.0:${PORT:-5000} --worker-class eventlet -w 1 --threads 2 --timeout 60 app:app

