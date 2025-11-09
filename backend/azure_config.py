"""
Azure Configuration Module
Store your Azure resource credentials here or use environment variables
"""
import os

# Azure Environment Flag
# Default: True (Azure environment)
# Set to False when running locally via python app.py
AzureEnvironment = True

# Cosmos DB (MongoDB API) Configuration
COSMOS_DB_URI = os.getenv('COSMOS_DB_URI', '')
# Format: mongodb://<account-name>:<account-key>@<account-name>.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@<account-name>@

COSMOS_DB_NAME = os.getenv('COSMOS_DB_NAME', 'tododb')

# Azure Storage Account Configuration (for file uploads)
AZURE_STORAGE_ACCOUNT_NAME = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '')
AZURE_STORAGE_ACCOUNT_KEY = os.getenv('AZURE_STORAGE_ACCOUNT_KEY', '')
AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'uploads')
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
# Alternative: Use connection string directly
# Format: DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net

# Application Settings
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Socket.IO CORS Origins (comma-separated for production)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Server Port (Azure will set PORT environment variable)
PORT = int(os.getenv('PORT', 5000))

# Maximum file upload size (16MB)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

