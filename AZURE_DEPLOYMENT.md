# Azure Deployment Guide

This guide will help you deploy the TaskFlow application to Azure using Cosmos DB (MongoDB API) and Azure Storage.

## Prerequisites

1. Azure account with active subscription
2. Azure CLI installed ([Install Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))
3. Python 3.11 (Azure Web App will use this)
4. GitHub repository (for auto-deployment)

## Step 1: Create Azure Resources

### 1.1 Create Resource Group

```bash
az group create --name taskflow-rg --location westeurope
```

### 1.2 Create Cosmos DB Account (MongoDB API)

```bash
# Create Cosmos DB account with MongoDB API
az cosmosdb create \
  --name taskflow-cosmosdb \
  --resource-group taskflow-rg \
  --kind MongoDB \
  --locations regionName=westeurope failoverPriority=0 \
  --default-consistency-level Session

# Create database (optional - will be created automatically)
az cosmosdb mongodb database create \
  --account-name taskflow-cosmosdb \
  --resource-group taskflow-rg \
  --name tododb
```

**Get Connection String:**
```bash
az cosmosdb keys list \
  --name taskflow-cosmosdb \
  --resource-group taskflow-rg \
  --type connection-strings
```

Copy the `PRIMARY CONNECTION STRING` value. Format it like:
```
mongodb://<account-name>:<primary-key>@<account-name>.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@<account-name>@
```

### 1.3 Create Azure Storage Account

```bash
# Create storage account
az storage account create \
  --name taskflowstorage \
  --resource-group taskflow-rg \
  --location westeurope \
  --sku Standard_LRS \
  --kind StorageV2

# Create blob container
az storage container create \
  --name uploads \
  --account-name taskflowstorage \
  --public-access blob
```

**Get Storage Connection String:**
```bash
az storage account show-connection-string \
  --name taskflowstorage \
  --resource-group taskflow-rg \
  --query connectionString \
  --output tsv
```

### 1.4 Create App Service Plan and Web App

```bash
# Create App Service Plan (B1 Basic tier recommended for production)
az appservice plan create \
  --name taskflow-plan \
  --resource-group taskflow-rg \
  --sku B1 \
  --is-linux

# Create Web App with Python 3.11
az webapp create \
  --resource-group taskflow-rg \
  --plan taskflow-plan \
  --name taskflow-app \
  --runtime "PYTHON|3.11"
```

## Step 2: Configure Environment Variables

Set the following application settings in Azure Web App:

```bash
# Cosmos DB Configuration
az webapp config appsettings set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --settings \
    COSMOS_DB_URI="mongodb://..." \
    COSMOS_DB_NAME="tododb" \
    MONGO_URI="mongodb://..."

# Azure Storage Configuration
az webapp config appsettings set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --settings \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..." \
    AZURE_STORAGE_ACCOUNT_NAME="taskflowstorage" \
    AZURE_STORAGE_CONTAINER_NAME="uploads"

# Application Settings
az webapp config appsettings set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --settings \
    FLASK_ENV="production" \
    FLASK_DEBUG="False" \
    CORS_ORIGINS="https://your-frontend-url.azurewebsites.net,https://your-custom-domain.com"
```

**Alternative:** Set via Azure Portal:
1. Go to Azure Portal → Your Web App → Configuration
2. Add application settings manually
3. Click "Save"

## Step 3: Configure Deployment

### 3.1 Enable Continuous Deployment from GitHub

**Via Azure Portal:**
1. Go to Azure Portal → Your Web App → Deployment Center
2. Select "GitHub" as source
3. Authorize and select your repository
4. Select branch: `azuredeployment` or `main`
5. Enable continuous deployment

### 3.2 Manual Deployment

```bash
# Install dependencies locally
cd backend
pip install -r requirements.txt

# Deploy using Azure CLI (if configured)
az webapp up \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --runtime "PYTHON|3.11"
```

### 3.3 Using GitHub Actions (Recommended)

1. **Get Publish Profile:**
   ```bash
   az webapp deployment list-publishing-profiles \
     --name taskflow-app \
     --resource-group taskflow-rg \
     --xml
   ```
   Copy the entire XML output.

2. **Add GitHub Secret:**
   - Go to your GitHub repository → Settings → Secrets → Actions
   - Add new secret: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Paste the XML content from step 1

3. **Update GitHub Actions workflow:**
   - Edit `.github/workflows/azure-deploy.yml`
   - Update `AZURE_WEBAPP_NAME` with your actual web app name

4. Push to the `azuredeployment` branch to trigger deployment.

## Step 4: Frontend Deployment

The frontend needs to be built and served. You have two options:

### Option A: Deploy Frontend to Static Web Apps or Azure Storage Static Website

```bash
# Build frontend
cd frontend
npm install
npm run build

# Deploy to Azure Static Web Apps (recommended)
# Or upload dist/ folder to Azure Storage static website
```

### Option B: Serve Frontend from the Same Web App

Modify the Flask app to serve static files:
- Add static file serving route
- Update CORS_ORIGINS to include your frontend URL

## Step 5: Configure Startup Command

Azure Web App needs a startup command. Set it via CLI:

```bash
az webapp config set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --startup-file "gunicorn --bind 0.0.0.0:8000 --worker-class eventlet -w 1 --threads 2 app:app"
```

Or via Portal:
1. Go to Azure Portal → Your Web App → Configuration → General Settings
2. Set Startup Command:
   ```
   gunicorn --bind 0.0.0.0:8000 --worker-class eventlet -w 1 --threads 2 app:app
   ```

## Step 6: Add Gunicorn to requirements.txt

Make sure `gunicorn` and `eventlet` are in requirements.txt (they should be added automatically).

## Step 7: Configuration File

You can also use `backend/azure_config.py` to hardcode values (NOT recommended for production):

1. Copy `azure_config.py` to `azure_config_local.py`
2. Fill in your Azure resource credentials
3. Keep `azure_config_local.py` in `.gitignore`

**Recommended:** Use environment variables instead of hardcoding.

## Troubleshooting

### View Application Logs

```bash
az webapp log tail \
  --name taskflow-app \
  --resource-group taskflow-rg
```

Or via Portal:
- Go to Web App → Log stream

### Common Issues

1. **Import Error:** Make sure all dependencies are in `requirements.txt`
2. **Connection to Cosmos DB fails:** Check connection string format
3. **File upload fails:** Verify Azure Storage connection string and container exists
4. **Socket.IO not working:** Ensure CORS is configured correctly and WebSocket is enabled

### Enable WebSocket

```bash
az webapp config set \
  --resource-group taskflow-rg \
  --name taskflow-app \
  --web-sockets-enabled true
```

## Cost Optimization

- Use **Cosmos DB Serverless** for development (auto-scales, pay per request)
- Use **Azure Storage Cool tier** for file storage if files are accessed infrequently
- Use **Basic App Service Plan** for development, scale up for production

## Security Recommendations

1. **Never commit secrets** to Git
2. Use **Azure Key Vault** for sensitive configuration
3. Enable **HTTPS only** on Web App
4. Configure **CORS** properly with specific origins
5. Use **Private Endpoints** for Cosmos DB and Storage in production

## Next Steps

1. Set up custom domain
2. Configure SSL certificates
3. Set up monitoring with Application Insights
4. Configure backup for Cosmos DB
5. Set up alerts for resource usage

## Support

For issues, check:
- [Azure Web Apps Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [Cosmos DB MongoDB API](https://docs.microsoft.com/en-us/azure/cosmos-db/mongodb/)
- [Azure Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/)

