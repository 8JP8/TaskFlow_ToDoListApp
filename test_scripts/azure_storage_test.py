"""
Test script for Azure Storage
Tests file upload, download, and listing with the provided connection string

Usage:
    python test_azure_storage.py
    
Or set environment variables:
    export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"
    python test_azure_storage.py
"""
import os
import sys
from io import BytesIO
from datetime import datetime

# Connection string must be provided via environment variable
# Format: DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net
CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'uploads')

# Validate that connection string is provided
if not CONNECTION_STRING:
    print("❌ Error: AZURE_STORAGE_CONNECTION_STRING environment variable is required!")
    print("\nPlease set the connection string as an environment variable:")
    print("  Windows PowerShell:")
    print("    $env:AZURE_STORAGE_CONNECTION_STRING=\"your_connection_string\"")
    print("  Windows CMD:")
    print("    set AZURE_STORAGE_CONNECTION_STRING=your_connection_string")
    print("  Linux/Mac:")
    print("    export AZURE_STORAGE_CONNECTION_STRING=\"your_connection_string\"")
    print("\nOr create a .env file in the project root with:")
    print("  AZURE_STORAGE_CONNECTION_STRING=your_connection_string")
    sys.exit(1)

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import AzureError
except ImportError:
    print("❌ Azure Storage SDK not installed!")
    print("Install it with: pip install azure-storage-blob")
    sys.exit(1)

def test_azure_storage():
    """Test Azure Storage operations"""
    print("=" * 60)
    print("🧪 Testing Azure Storage Connection")
    print("=" * 60)
    
    try:
        # Initialize client
        print("\n1️⃣ Initializing BlobServiceClient...")
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        print("✅ BlobServiceClient created successfully")
        
        # Get container client
        print(f"\n2️⃣ Getting container client for '{CONTAINER_NAME}'...")
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Try to create container (will fail if it exists, that's ok)
        try:
            container_client.create_container()
            print(f"✅ Container '{CONTAINER_NAME}' created")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e) or "already exists" in str(e).lower():
                print(f"ℹ️ Container '{CONTAINER_NAME}' already exists")
            else:
                print(f"⚠️ Container creation error (may still work): {e}")
        
        # Test upload
        print(f"\n3️⃣ Testing file upload...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"test_file_{timestamp}.txt"
        test_content = f"This is a test file content from Python script!\nCreated at: {datetime.now().isoformat()}\nTest successful!".encode('utf-8')
        test_file = BytesIO(test_content)
        
        blob_client = container_client.get_blob_client(test_filename)
        blob_client.upload_blob(test_content, overwrite=True)
        print(f"✅ File '{test_filename}' uploaded successfully")
        
        # Get blob URL
        blob_url = blob_client.url
        print(f"📍 Blob URL: {blob_url}")
        
        # Test download
        print(f"\n4️⃣ Testing file download...")
        downloaded_content = blob_client.download_blob().readall()
        print(f"✅ File downloaded successfully ({len(downloaded_content)} bytes)")
        print(f"📄 Content: {downloaded_content.decode('utf-8')[:50]}...")
        
        # Test listing blobs
        print(f"\n5️⃣ Testing blob listing...")
        # list_blobs() returns an iterator, not a list
        # Use itertools.islice or limit manually
        from itertools import islice
        blob_iterator = container_client.list_blobs()
        blobs = list(islice(blob_iterator, 10))  # Get first 10 blobs
        print(f"✅ Found {len(blobs)} blobs in container (showing first 10):")
        for blob in blobs[:5]:  # Show first 5
            print(f"   - {blob.name} ({blob.size} bytes)")
        if len(blobs) > 5:
            print(f"   ... and {len(blobs) - 5} more")
        
        # Test delete
        print(f"\n6️⃣ Testing file delete...")
        blob_client.delete_blob()
        print(f"✅ File '{test_filename}' deleted successfully")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Azure Storage is working correctly.")
        print("=" * 60)
        
    except AzureError as e:
        print(f"\n❌ Azure Storage Error: {e}")
        print(f"Error Code: {getattr(e, 'error_code', 'N/A')}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_azure_storage()
    sys.exit(0 if success else 1)

