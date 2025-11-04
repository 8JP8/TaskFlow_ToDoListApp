# Quick Start - Azure Deployment

## 📋 Summary

Your application is now configured for Azure deployment with:
- ✅ Cosmos DB (MongoDB API) support
- ✅ Azure Storage for file uploads
- ✅ Environment variable configuration
- ✅ GitHub Actions for auto-deployment
- ✅ Gunicorn production server

## 🚀 Quick Deployment Steps

### 1. Create Azure Resources (One-time setup)

```bash
# Login to Azure
az login

# Create resource group
az group create --name taskflow-rg --location westeurope

# Create Cosmos DB
az cosmosdb create --name taskflow-cosmosdb --resource-group taskflow-rg --kind MongoDB --locations regionName=westeurope

# Create Storage Account
az storage account create --name taskflowstorage --resource-group taskflow-rg --location westeurope --sku Standard_LRS

# Create Web App
az appservice plan create --name taskflow-plan --resource-group taskflow-rg --sku B1 --is-linux
az webapp create --resource-group taskflow-rg --plan taskflow-plan --name taskflow-app --runtime "PYTHON|3.11"
```

### 2. Get Connection Strings

```bash
# Cosmos DB connection string
az cosmosdb keys list --name taskflow-cosmosdb --resource-group taskflow-rg --type connection-strings

# Storage connection string
az storage account show-connection-string --name taskflowstorage --resource-group taskflow-rg
```

### 3. Configure Environment Variables

```bash
az webapp config appsettings set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --settings \
    COSMOS_DB_URI="mongodb://..." \
    COSMOS_DB_NAME="tododb" \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..." \
    AZURE_STORAGE_ACCOUNT_NAME="taskflowstorage" \
    AZURE_STORAGE_CONTAINER_NAME="uploads" \
    FLASK_ENV="production" \
    CORS_ORIGINS="*"
```

### 4. Set Startup Command

```bash
az webapp config set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --startup-file "gunicorn --bind 0.0.0.0:8000 --worker-class eventlet -w 1 --threads 2 app:app"
```

### 5. Enable WebSocket

```bash
az webapp config set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --web-sockets-enabled true
```

### 6. Configure GitHub Actions (Auto-Deploy)

1. Get publish profile:
   ```bash
   az webapp deployment list-publishing-profiles --name taskflow-app --resource-group taskflow-rg --xml
   ```

2. Add GitHub Secret:
   - Repository → Settings → Secrets → Actions
   - Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Value: (paste XML from step 1)

3. Update `.github/workflows/azure-deploy.yml`:
   - Change `AZURE_WEBAPP_NAME` to your actual web app name

4. Push to `azuredeployment` branch to trigger deployment!

## 📝 Configuration File

You can also use `backend/azure_config.py` to set default values (development only).

For production, **always use environment variables** set in Azure Portal.

## 🔍 Storage Account Type

Create a **Standard Storage Account** (General Purpose v2) with:
- **Performance:** Standard
- **Redundancy:** LRS (Locally Redundant Storage) for development
- **Access tier:** Hot
- **Container name:** `uploads` (created automatically)

## 📚 Full Documentation

See `AZURE_DEPLOYMENT.md` for detailed instructions and troubleshooting.

