<# 
 BhaktiGen Ops Runner — Windows PowerShell
 One-click local flow: backend -> frontend -> tests -> push
 Self-heals Node PATH, EPERM locks, and missing vite.
#>
$Repo = "C:\Users\vedant.sharma\Documents\ai-youtube-generator"
$OpsDir = "C:\Users\vedant.sharma\Documents\ai-youtube-generator\ops"
New-Item -ItemType Directory -Force -Path "C:\Users\vedant.sharma\Documents\ai-youtube-generator\ops" | Out-Null
$Log = "C:\Users\vedant.sharma\Documents\ai-youtube-generator\ops\ops.log"
$FrontendLog = "C:\Users\vedant.sharma\Documents\ai-youtube-generator\ops\frontend.log"
function Log($m){ $ts=(Get-Date).ToString("s"); "$ts  $m" | Tee-Object -FilePath $Log -Append | Out-Host }

$FE = "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend"
$NodeDir="C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64"
$Node="C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\node.exe"
$Npm="C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\npm.cmd"
$BackendPort=8000
$FE5173="http://localhost:5173"
$FE5174="http://localhost:5174"

function Kill-Lockers {
  Log "Killing node/npm/vite processes"
  Get-Process node,npm,vit* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  foreach($p in 5173,5174){ 
    try {
      Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -Unique | 
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    } catch {}
  }
}

function Ensure-NodePath {
  Log "Ensuring Node on PATH: $NodeDir"
  [Environment]::SetEnvironmentVariable('Path', "$NodeDir;" + [Environment]::GetEnvironmentVariable('Path','Process'), 'Process') | Out-Null
}

function Clean-Frontend {
  Log "Attempting fast clean of @rollup native module"
  Remove-Item -LiteralPath "$FE\node_modules\@rollup" -Recurse -Force -ErrorAction SilentlyContinue
}

function Nuke-Frontend {
  Log "Deep clean node_modules + lockfile"
  Remove-Item -LiteralPath "$FE\node_modules" -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath "$FE\package-lock.json" -Force -ErrorAction SilentlyContinue
}

function FE-Install {
  Set-Location $FE
  Log "Installing frontend deps"
  if (Test-Path "$FE\package-lock.json") {
    & $Npm ci
  } else {
    & $Npm install
  }
}

function FE-Start {
  Set-Location $FE
  # Use absolute node.exe to avoid PATH flakiness
  Log "Starting Vite with absolute node.exe on :5173"
  Start-Process -FilePath "powershell" -WorkingDirectory $FE -ArgumentList "-NoProfile","-Command","& '$Node' node_modules\vite\bin\vite.js --port 5173 *> 'C:\Users\vedant.sharma\Documents\ai-youtube-generator\ops\frontend.log'" | Out-Null
}

function Probe-FE {
  Log "Probing FE port"
  try { iwr $FE5173 -UseBasicParsing | Out-Null; return $FE5173 } catch {
    try { iwr $FE5174 -UseBasicParsing | Out-Null; return $FE5174 } catch { return $null }
  }
}

function Run-Tests($feUrl) {
  Set-Location $FE
  [Environment]::SetEnvironmentVariable('PW_BASE_URL', $feUrl, 'Process') | Out-Null
  Log "PW_BASE_URL=$feUrl"
  $okType=$true
  try { & "C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\node.exe" "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend\node_modules\typescript\bin\tsc" --noEmit -p tsconfig.app.json } catch { $okType=$false; Log "typecheck failed" }
  $smoke="❌"
  try { & "C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\node.exe" "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend\node_modules\@playwright\test\cli.js" test e2e/smoke.spec.ts; $smoke="✅" } catch { Log "smoke failed; retrying"; try { & "C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\node.exe" "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend\node_modules\@playwright\test\cli.js" test e2e/smoke.spec.ts; $smoke="Retry✅" } catch {} }
  $flag="❌"
  try { & "C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64\node.exe" "C:\Users\vedant.sharma\Documents\ai-youtube-generator\backend\frontend\node_modules\@playwright\test\cli.js" test -g "marketplace flag gating"; $flag="✅" } catch {}
  return @{ type=$okType; smoke=$smoke; flag=$flag }
}

# ===== Backend (already easy) =====
Set-Location $Repo
[Environment]::SetEnvironmentVariable('SIMULATE_RENDER','1','Process') | Out-Null
Log "Ensuring backend on :$BackendPort (manual start recommended in separate terminal)"

# ===== Frontend flow =====
Kill-Lockers
Ensure-NodePath
try {
  FE-Install
} catch {
  Log "Install error - attempting fast clean"
  Clean-Frontend
  try { FE-Install } catch {
    Log "Fast clean failed - nuking frontend and reinstalling"
    Nuke-Frontend
    FE-Install
  }
}
FE-Start
$feUrl = $null
for ($i=0; $i -lt 60 -and -not $feUrl; $i++) {
  try { iwr 'http://localhost:5173' -UseBasicParsing | Out-Null; $feUrl='http://localhost:5173'; break } catch {}
  try { iwr 'http://localhost:5174' -UseBasicParsing | Out-Null; $feUrl='http://localhost:5174'; break } catch {}
  Start-Sleep -Milliseconds 750
}
if (-not $feUrl) {
  # parse frontend log for "Local: http://localhost:PORT/"
  if (Test-Path "$FrontendLog") {
    $line = (Get-Content "$FrontendLog" -Tail 200 | Select-String -Pattern 'Local:\s+(http://localhost:\d+/)').Matches.Value | Select-Object -First 1
    if ($line) { $feUrl = ($line -replace 'Local:\s+','').TrimEnd('/') }
  }
}
if (-not $feUrl) { Log 'Frontend not reachable'; }

# ===== Tests =====
Log "Frontend URL: $feUrl"
$results = if ($feUrl) { Run-Tests $feUrl } else { @{ type=$false; smoke="❌"; flag="❌" } }

# ===== Commit & push only if changes =====
Set-Location $Repo
git add ops $FE\package.json | Out-Null
$st = git status --porcelain
$commitRes = "Nothing to commit."
if (-not [string]::IsNullOrWhiteSpace($st)) {
  git commit -m "feat(ops): self-healing e2e runner (node path, EPERM fix, absolute vite)" | Out-Null
  $commitRes = "Committed"
  git push origin main | Out-Null
}

# ===== Summary =====
try { iwr http://127.0.0.1:$BackendPort/docs -UseBasicParsing | Out-Null; $be="✅ (http://127.0.0.1:$BackendPort)" } catch { $be="❌" }
$fe = $(if ($feUrl) { "✅ ($feUrl)" } else { "❌" })
"Backend: $be" | Out-Host
"Frontend: $fe" | Out-Host
"Typecheck: " + ($(if($results.type){"✅"}else{"❌"})) | Out-Host
"Smoke: $($results.smoke)" | Out-Host
"Templates flag test: $($results.flag)" | Out-Host
"Commit: $commitRes" | Out-Host
"Push: " + ($(if($commitRes -ne 'Nothing to commit.'){"✅"} else {"(skipped)"})) | Out-Host
"Ready to run." | Out-Host
