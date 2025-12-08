# scripts/setup-node-and-build.ps1
# Portable Node.js + frontend typecheck/build (no admin)

$ErrorActionPreference = "Stop"

# 0) Config
$ver = "22.21.1"
$zipUrl = "https://nodejs.org/dist/v$ver/node-v$ver-win-x64.zip"
$tools = Join-Path $env:USERPROFILE "tools\node-$ver"
$zip   = "$tools.zip"
$nodeHome = Join-Path $tools "node-v$ver-win-x64"
$frontend = "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend"

# 1) Ensure folders and download Node if missing
if (-not (Test-Path $nodeHome)) {
  New-Item -ItemType Directory -Force -Path $tools | Out-Null
  Write-Host "[INFO] Downloading Node v$ver..."
  Invoke-WebRequest $zipUrl -OutFile $zip -UseBasicParsing
  Write-Host "[INFO] Extracting..."
  Expand-Archive -Path $zip -DestinationPath $tools -Force
}

# 2) Put Node on PATH for this session
$env:PATH = "$nodeHome;$env:PATH"
Write-Host "[INFO] Using Node: $(& "$nodeHome\node.exe" -v)"
Write-Host "[INFO] Using npm : $(& "$nodeHome\npm.cmd" -v)"

# 3) Build frontend
if (-not (Test-Path $frontend)) {
  throw "Frontend path not found: $frontend"
}

Push-Location $frontend
try {
  # optional: enable corepack (harmless if not present)
  try { & "$nodeHome\npx.cmd" corepack enable | Out-Null } catch {}

  if (Test-Path "package-lock.json") {
    & "$nodeHome\npm.cmd" ci
  } else {
    & "$nodeHome\npm.cmd" install
  }

  & "$nodeHome\npm.cmd" run typecheck
  & "$nodeHome\npm.cmd" run build
}
finally {
  Pop-Location
}

# 4) Summary
Write-Host "----- SUMMARY -----"
Write-Host "Node: $(& "$nodeHome\node.exe" -v)"
Write-Host "npm : $(& "$nodeHome\npm.cmd" -v)"
if (Test-Path "$frontend\dist") {
  Write-Host "Build: dist/ created"
} elseif (Test-Path "$frontend\build") {
  Write-Host "Build: build/ created"
} else {
  Write-Host "Build output not found (dist/ or build/)."
}
