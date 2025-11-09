"""
Azure Storage Helper Module
Handles file uploads to Azure Blob Storage
Uses environment variables or azure_config module
"""
import os
import uuid
from werkzeug.utils import secure_filename
import logging

# Import azure_config if available
try:
    import azure_config
except ImportError:
    azure_config = None

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
        # Get credentials from azure_config module or environment variables
        # Priority: azure_config module > environment variables
        if azure_config:
            self.account_name = azure_config.AZURE_STORAGE_ACCOUNT_NAME or os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '')
            self.account_key = azure_config.AZURE_STORAGE_ACCOUNT_KEY or os.getenv('AZURE_STORAGE_ACCOUNT_KEY', '')
            self.connection_string = azure_config.AZURE_STORAGE_CONNECTION_STRING or os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
            self.container_name = azure_config.AZURE_STORAGE_CONTAINER_NAME or os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'uploads')
        else:
            # Fallback to environment variables only
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
            print("⚠️ Azure Storage SDK not installed. Install with: pip install azure-storage-blob")
            return
            
        try:
            # Clean connection string (remove any extra spaces/newlines)
            connection_string = self.connection_string.strip() if self.connection_string else ''
            
            if connection_string:
                # Use connection string if available (preferred method)
                print(f"🔗 Initializing Azure Storage with connection string...")
                print(f"📍 Account: {self.account_name or 'from connection string'}")
                print(f"📦 Container: {self.container_name}")
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
            elif self.account_name and self.account_key:
                # Use account name and key (fallback)
                print(f"🔗 Initializing Azure Storage with account credentials...")
                print(f"📍 Account: {self.account_name}")
                print(f"📦 Container: {self.container_name}")
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                credential = AzureNamedKeyCredential(self.account_name, self.account_key)
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
            else:
                logger.warning("Azure Storage credentials not found. Files will not be uploaded to Azure.")
                print("⚠️ Azure Storage credentials not found. Using local storage.")
                return
            
            # Get or create container
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            try:
                self.container_client.create_container()
                print(f"✅ Container '{self.container_name}' created/verified")
            except Exception as e:
                # Container already exists or other error
                if "ContainerAlreadyExists" in str(e) or "already exists" in str(e).lower():
                    print(f"ℹ️ Container '{self.container_name}' already exists")
                else:
                    print(f"⚠️ Container check: {str(e)}")
                    # Don't fail if container exists
                    pass
                
            print("✅ Azure Storage client initialized successfully")
                
        except AzureError as e:
            logger.error(f"Azure Storage initialization error: {str(e)}")
            print(f"❌ Azure Storage initialization failed: {str(e)}")
            self.blob_service_client = None
            self.container_client = None
        except Exception as e:
            logger.error(f"Error initializing Azure Storage client: {str(e)}")
            print(f"❌ Error initializing Azure Storage: {str(e)}")
            import traceback
            traceback.print_exc()
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

