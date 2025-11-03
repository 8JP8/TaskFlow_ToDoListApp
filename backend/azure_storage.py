"""
Azure Storage Helper Module
Handles file uploads to Azure Blob Storage
"""
import os
import uuid
from werkzeug.utils import secure_filename
import logging

# Optional Azure Storage imports - only import if available
try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    from azure.core.credentials import AzureNamedKeyCredential
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    # Azure Storage SDK not installed - use local storage only
    AZURE_AVAILABLE = False
    BlobServiceClient = None
    BlobClient = None
    ContainerClient = None
    AzureNamedKeyCredential = None
    AzureError = Exception

logger = logging.getLogger(__name__)

class AzureStorageManager:
    def __init__(self):
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '')
        self.account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY', '')
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'uploads')
        self.blob_service_client = None
        self.container_client = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Blob Storage client"""
        # If Azure SDK is not installed, don't try to initialize
        if not AZURE_AVAILABLE:
            logger.info("Azure Storage SDK not installed. Using local storage only.")
            return
            
        try:
            if self.connection_string:
                # Use connection string if available
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_name and self.account_key:
                # Use account name and key
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                credential = AzureNamedKeyCredential(self.account_name, self.account_key)
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
            else:
                logger.warning("Azure Storage credentials not found. Files will not be uploaded to Azure.")
                return
            
            # Get or create container
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            try:
                self.container_client.create_container()
            except Exception:
                # Container already exists, that's fine
                pass
                
        except Exception as e:
            logger.error(f"Error initializing Azure Storage client: {str(e)}")
            self.blob_service_client = None
            self.container_client = None
    
    def is_configured(self):
        """Check if Azure Storage is properly configured"""
        return self.blob_service_client is not None and self.container_client is not None
    
    def upload_file(self, file, filename=None):
        """
        Upload a file to Azure Blob Storage
        Returns the blob URL or None if upload fails
        """
        if not AZURE_AVAILABLE or not self.is_configured():
            logger.warning("Azure Storage not available or not configured, returning None")
            return None
        
        try:
            # Generate unique filename
            if not filename:
                secure_name = secure_filename(file.filename) if hasattr(file, 'filename') else 'file'
                unique_filename = f"{uuid.uuid4()}_{secure_name}"
            else:
                unique_filename = filename
            
            # Upload to blob storage
            blob_client = self.container_client.get_blob_client(unique_filename)
            
            # If file is a file-like object, read it
            if hasattr(file, 'read'):
                file_content = file.read()
                blob_client.upload_blob(file_content, overwrite=True)
            else:
                # If it's already bytes
                blob_client.upload_blob(file, overwrite=True)
            
            # Return the blob URL
            blob_url = blob_client.url
            return {
                'unique_filename': unique_filename,
                'blob_url': blob_url,
                'filename': secure_filename(file.filename) if hasattr(file, 'filename') else unique_filename
            }
            
        except AzureError as e:
            logger.error(f"Azure Storage upload error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return None
    
    def delete_file(self, blob_name):
        """
        Delete a file from Azure Blob Storage
        """
        if not AZURE_AVAILABLE or not self.is_configured():
            return False
        
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except AzureError as e:
            logger.error(f"Azure Storage delete error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"File delete error: {str(e)}")
            return False
    
    def get_file_url(self, blob_name):
        """
        Get the URL for a blob
        """
        if not AZURE_AVAILABLE or not self.is_configured():
            return None
        
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.url
        except Exception as e:
            logger.error(f"Error getting blob URL: {str(e)}")
            return None

# Global instance
azure_storage = AzureStorageManager()

