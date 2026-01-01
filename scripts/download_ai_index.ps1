Param(
    [string]$Url = "https://example.com/ai_index.pkl",
    [string]$Out = "projects/bot/python_bot/data/ai_index.pkl"
)

if (-not (Test-Path (Split-Path $Out -Parent))) {
    New-Item -ItemType Directory -Path (Split-Path $Out -Parent) -Force | Out-Null
}

Write-Host "Downloading ai_index from $Url to $Out"
try {
    Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing -ErrorAction Stop
    Write-Host "Download completed."
} catch {
    Write-Error "Download failed: $_"
    exit 1
}
