# Production Guardian - Azure Teardown / Cleanup Script
param (
    [string]$ResourceGroup = "production-guardian-rg"
)

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "   Production Guardian - Azure Teardown Script    " -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow

# Refresh PATH to pick up Azure CLI if newly installed
$azureCliPath = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"
if (Test-Path $azureCliPath) {
    if ($env:Path -notlike "*$azureCliPath*") {
        $env:Path = "$azureCliPath;$env:Path"
    }
}

# Verify Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') is not found in PATH."
    exit 1
}

Write-Host "`nChecking Resource Group: $ResourceGroup..." -ForegroundColor Cyan
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -ne "true") {
    Write-Host "Resource Group '$ResourceGroup' does not exist. Nothing to clean up." -ForegroundColor Green
    exit 0
}

Write-Host "`nWARNING: This will permanently delete resource group '$ResourceGroup' and all its resources (VM, disks, IPs, NSGs)." -ForegroundColor Red
$confirmation = Read-Host "Are you sure you want to delete everything? (y/N)"
if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host "`nDeleting resource group '$ResourceGroup' (this runs in the background on Azure)..." -ForegroundColor Cyan
az group delete --name $ResourceGroup --yes --no-wait

Write-Host "`nSuccess! Deletion initiated for '$ResourceGroup'." -ForegroundColor Green
Write-Host "All Azure computing and storage charges for this deployment have been stopped." -ForegroundColor Green
