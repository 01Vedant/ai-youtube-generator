param(
  [string]$OutputPath = "backups",
  [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dest = Join-Path $OutputPath "db-$timestamp.sqlite"

$src = "platform/backend/data/app.db"
Copy-Item $src $dest -Force

Get-ChildItem $OutputPath -Filter "db-*.sqlite" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } | Remove-Item -Force
Write-Output "Backup completed: $dest"
