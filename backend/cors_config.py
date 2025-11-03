"""
CORS Configuration Module
Configure allowed origins for CORS and Socket.IO
"""
import os

# Enable/Disable CORS module
# Set via environment variable USE_CORS (default: True)
# Set to 'False' or '0' to disable CORS
USE_CORS = os.getenv('USE_CORS', 'True').lower() in ('true', '1', 'yes')

# CORS Allowed Origins
# Set via environment variable CORS_ORIGINS (comma-separated)
# Or override this list directly in this file
CORS_ORIGINS = [
    "https://taskflowrinte.azurewebsites.net",
    "https://taskflow.pt",
    "http://localhost:8080",
    "http://localhost:5000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5000"
]

# Allow environment variable to override the list
env_origins = os.getenv('CORS_ORIGINS', '').strip()
if env_origins and env_origins != '*':
    # Parse comma-separated origins from environment variable
    CORS_ORIGINS = [origin.strip() for origin in env_origins.split(',') if origin.strip()]

# Socket.IO allowed origins (same as CORS)
SOCKETIO_CORS_ORIGINS = CORS_ORIGINS.copy()

