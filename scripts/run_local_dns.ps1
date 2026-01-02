Param(
    [string]$Domain = 'torrents.local',
    [string]$Address = '127.0.0.1'
)

# Run the Python local DNS server in background. Requires running PowerShell as Administrator
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { Write-Error 'Python not found in PATH'; exit 1 }

$args = "tools/local_dns.py --domain $Domain --address $Address"
Write-Output "Starting local DNS: python $args"

# Start elevated if possible (this will prompt UAC)
Try {
    Start-Process -FilePath $py -ArgumentList $args -Verb RunAs -WindowStyle Hidden
    Write-Output 'Local DNS started (elevated).'
} Catch {
    # Fallback: start without elevation (may fail to bind port 53)
    Start-Process -FilePath $py -ArgumentList $args -NoNewWindow -WindowStyle Hidden
    Write-Output 'Local DNS started (non-elevated). If binding to port 53 failed, run as Administrator.'
}
