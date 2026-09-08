<#
.SYNOPSIS
    Production Guardian - Automated Azure Deployment Script
    Provisions an Azure Linux VM, installs Docker, launches all services via Docker Compose,
    and seeds realistic film production incident scenarios.

.EXAMPLE
    .\deploy_azure_vm.ps1 -Location "eastus" -VmSize "Standard_B2s"
#>

param (
    [string]$ResourceGroup = "production-guardian-rg",
    [string]$Location = "eastus",
    [string]$VmName = "guardian-vm",
    [string]$VmSize = "Standard_B2s",
    [string]$AdminUsername = "azureuser",
    [string]$RepoUrl = "https://github.com/ajayg10/production-guardian.git"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "       Production Guardian - Azure Cloud Automated Deployer     " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Refresh PATH to pick up Azure CLI if newly installed
$azureCliPath = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"
if (Test-Path $azureCliPath) {
    if ($env:Path -notlike "*$azureCliPath*") {
        $env:Path = "$azureCliPath;$env:Path"
    }
}

# 2. Verify Azure CLI exists
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') was not found in PATH. Please ensure the Azure CLI installer has completed."
    exit 1
}

Write-Host "`n[1/6] Verifying Azure Authentication..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not currently logged into Azure. Launching interactive browser login..." -ForegroundColor Yellow
    az login --output none
    $account = az account show | ConvertFrom-Json
}
Write-Host "Authenticated as: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green

# 3. Read Local .env for secrets & credentials
$localEnvPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $localEnvPath)) {
    $localEnvPath = Join-Path $PSScriptRoot ".env.example"
}

Write-Host "`n[2/6] Reading local environment configuration..." -ForegroundColor Yellow
$envVars = @{}
Get-Content $localEnvPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

# 4. Create Resource Group
Write-Host "`n[3/6] Setting up Resource Group '$ResourceGroup' in '$Location'..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output table

# 5. Create Virtual Machine
Write-Host "`n[4/6] Provisioning Azure VM '$VmName' ($VmSize)..." -ForegroundColor Yellow
Write-Host "This usually takes about 60-90 seconds..." -ForegroundColor Gray

az vm create `
    --resource-group $ResourceGroup `
    --name $VmName `
    --image Ubuntu2204 `
    --size $VmSize `
    --admin-username $AdminUsername `
    --generate-ssh-keys `
    --output table

# Open Required Network Ports
Write-Host "Opening network ports (3000=Frontend, 8000=FastAPI/MCP, 22=SSH)..." -ForegroundColor Gray
az vm open-port --resource-group $ResourceGroup --name $VmName --port 3000 --priority 1001 --output none
az vm open-port --resource-group $ResourceGroup --name $VmName --port 8000 --priority 1002 --output none

# Get Public IP
$publicIp = (az vm show -d -g $ResourceGroup -n $VmName --query publicIps -o tsv).Trim()
Write-Host "VM Public IP: $publicIp" -ForegroundColor Green

# 6. Remote Provisioning via Azure Run-Command
Write-Host "`n[5/6] Remotely provisioning software on the VM..." -ForegroundColor Yellow
Write-Host "- Installing Docker & Docker Compose" -ForegroundColor Gray
Write-Host "- Cloning repository: $RepoUrl" -ForegroundColor Gray
Write-Host "- Building and starting containers" -ForegroundColor Gray
Write-Host "- Seeding realistic production incidents" -ForegroundColor Gray

# Prepare Remote Script
$googleApiKey = $envVars["GOOGLE_API_KEY"]
$grafanaUrl = $envVars["GRAFANA_URL"]
$grafanaToken = $envVars["GRAFANA_SERVICE_ACCOUNT_TOKEN"]
$grafanaRemoteWrite = $envVars["GRAFANA_PROMETHEUS_REMOTE_WRITE_URL"]
$grafanaUser = $envVars["GRAFANA_PROMETHEUS_USER_ID"]
$grafanaApiKey = $envVars["GRAFANA_PROMETHEUS_API_KEY"]
$grafanaMcpUrl = $envVars["GRAFANA_MCP_URL"]

$remoteScriptContent = @"
#!/usr/bin/env bash
set -e

# Update and install Docker
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl docker.io docker-compose-v2
systemctl enable --now docker

# Setup application directory
mkdir -p /opt/production-guardian
cd /opt

if [ ! -d "/opt/production-guardian/.git" ]; then
    git clone $RepoUrl production-guardian
fi

cd /opt/production-guardian
git fetch --all
git reset --hard origin/main

# Generate remote production .env
cat << 'EOF' > .env
APP_ENV=production
NEXT_PUBLIC_API_URL=http://$publicIp:8000
FRONTEND_URL=http://$publicIp:3000
DATABASE_URL=postgresql+asyncpg://guardian:guardian@postgres:5432/production_guardian
DATABASE_SYNC_URL=postgresql://guardian:guardian@postgres:5432/production_guardian
POSTGRES_USER=guardian
POSTGRES_PASSWORD=guardian
POSTGRES_DB=production_guardian
POSTGRES_PORT=5432
GOOGLE_API_KEY=$googleApiKey
GEMINI_MODEL=gemini-1.5-pro
GRAFANA_URL=$grafanaUrl
GRAFANA_SERVICE_ACCOUNT_TOKEN=$grafanaToken
GRAFANA_MCP_URL=$grafanaMcpUrl
GRAFANA_PROMETHEUS_REMOTE_WRITE_URL=$grafanaRemoteWrite
GRAFANA_PROMETHEUS_USER_ID=$grafanaUser
GRAFANA_PROMETHEUS_API_KEY=$grafanaApiKey
EOF

# Build and start all 4 services
docker compose down -v || true
docker compose up -d --build

# Wait for API to be healthy
echo "Waiting for API to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
        echo "API is healthy!"
        break
    fi
    sleep 3
done

# Seed initial scenes and realistic production incidents
echo "Seeding incident database..."
docker compose exec -T api python /app/database/seed/seed.py --count 10

echo "DEPLOYMENT_COMPLETE"
"@

# Save temporary script for Azure CLI invocation
$tempScriptPath = Join-Path $env:TEMP "azure_remote_deploy.sh"
[System.IO.File]::WriteAllText($tempScriptPath, $remoteScriptContent.Replace("`r`n", "`n"))

Write-Host "Executing remote deployment on Azure VM (this takes 2-4 minutes)..." -ForegroundColor Cyan
$cmdResult = az vm run-command invoke `
    --resource-group $ResourceGroup `
    --name $VmName `
    --command-id RunShellScript `
    --scripts "@$tempScriptPath" `
    --output json | ConvertFrom-Json

# Clean up temp file
Remove-Item -Path $tempScriptPath -Force -ErrorAction SilentlyContinue

Write-Host "`n[6/6] Deployment finished!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   PRODUCTION GUARDIAN IS LIVE ON AZURE! 🚀" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "Frontend Dashboard : http://$publicIp:3000" -ForegroundColor Cyan
Write-Host "Incidents Log      : http://$publicIp:3000/incidents" -ForegroundColor Cyan
Write-Host "FastAPI Swagger    : http://$publicIp:8000/api/docs" -ForegroundColor Cyan
Write-Host "Health Check       : http://$publicIp:8000/api/health" -ForegroundColor Cyan
Write-Host "Grafana MCP Gateway: http://$publicIp:8000/mcp" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Green
Write-Host "To stop or delete this deployment when done, run:" -ForegroundColor Yellow
Write-Host ".\deploy_azure_cleanup.ps1 -ResourceGroup '$ResourceGroup'" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Green
