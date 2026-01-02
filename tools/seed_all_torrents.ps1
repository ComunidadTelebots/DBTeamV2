# PowerShell script to seed todos los .torrent de la carpeta data/torrents con webtorrent-hybrid
# Requiere tener instalado Node.js y webtorrent-hybrid (npm install -g webtorrent-hybrid)

$TorrentDir = "data/torrents"
$Torrents = Get-ChildItem -Path $TorrentDir -Filter *.torrent

foreach ($torrent in $Torrents) {
    Write-Host "Seedeando: $($torrent.FullName)"
    Start-Process -NoNewWindow -FilePath "webtorrent-hybrid" -ArgumentList '"' + $torrent.FullName + '" --keep-seeding'
}

Write-Host "Todos los torrents están siendo seedeados por webtorrent-hybrid."
