# Ops runner for BhaktiGen (local machine)
# Starts backend+frontend, probes ports, runs typecheck+E2E, commits & pushes.
New-Item -ItemType Directory -Force -Path ops | Out-Null
$Log="ops/ops.log"
function Log($m){ $ts=(Get-Date).ToString("s"); "$ts  $m" | Tee-Object -FilePath $Log -Append | Out-Host }
function Kill-Port($p){ try{ (Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Select -Expand OwningProcess -Unique) | % { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Log "Killed PID $_ on :$p" } }catch{} }
function Wait-Http($u,$t=30){ $sw=[Diagnostics.Stopwatch]::StartNew(); while($sw.Elapsed.TotalSeconds -lt $t){ try{ $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 5; if($r.StatusCode -ge 200){ return $true } }catch{ Start-Sleep -Milliseconds 400 } }; return $false }
function PortUp($p){ (Test-NetConnection -ComputerName 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded }

# constants
$NodeDir="C:\Users\vedant.sharma\Documents\node-v24.11.1-win-x64"
$FEPath="backend/frontend"
$BackendPort=8000
$FE5173="http://localhost:5173"
$FE5174="http://localhost:5174"

# clean ports
Kill-Port $BackendPort; Kill-Port 5173; Kill-Port 5174

# backend
$env:SIMULATE_RENDER="1"
$BackendLog="ops/backend.log"
Log "Starting backend on :$BackendPort"
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-Command","uvicorn backend.backend.main:app --port $BackendPort --reload *>$BackendLog" | Out-Null
if(!(PortUp $BackendPort) -and !(Wait-Http "http://127.0.0.1:$BackendPort/docs" 30)){ Log "Backend failed to start"; Get-Content $BackendLog -ea SilentlyContinue | Select -Last 100 | Tee-Object -FilePath $Log -Append | Out-Null }

# frontend
$FrontendLog="ops/frontend.log"
Push-Location $FEPath
$env:PATH="$NodeDir;$env:PATH"
Log "Starting Vite on :5173 (fallback :5174)"
Start-Process -FilePath "powershell" -WorkingDirectory "$PWD" -ArgumentList "-NoProfile","-Command","npm run dev -- --port 5173 *>$($PWD)\..\..\ops\frontend.log" | Out-Null
Pop-Location

# detect FE URL
$FEURL=$null
if(Wait-Http $FE5173 25){ $FEURL=$FE5173 } elseif(Wait-Http $FE5174 20){ $FEURL=$FE5174 } else { Log "Frontend not reachable on 5173/5174"; Get-Content $FrontendLog -ea SilentlyContinue | Select -Last 200 | Tee-Object -FilePath $Log -Append | Out-Null }

# typecheck + tests
Push-Location $FEPath
if($FEURL){ $env:PW_BASE_URL=$FEURL } else { $env:PW_BASE_URL=$FE5173 }
Log "PW_BASE_URL=$($env:PW_BASE_URL)"

$TypeOk=$true; try{ cmd /c "npm run typecheck" | Tee-Object -FilePath ..\..\ops\ops.log -Append | Out-Null } catch { $TypeOk=$false; Log "typecheck failed" }
$Smoke="❌"; try{ cmd /c "npm run e2e:smoke" | Tee-Object -FilePath ..\..\ops\ops.log -Append | Out-Null; $Smoke="✅" } catch { Log "smoke failed; retrying"; try{ cmd /c "npm run e2e:smoke" | Tee-Object -FilePath ..\..\ops\ops.log -Append | Out-Null; $Smoke="Retry✅" } catch { $Smoke="❌" } }
$Flag="❌"; try{ cmd /c "npm run e2e:flag"  | Tee-Object -FilePath ..\..\ops\ops.log -Append | Out-Null; $Flag="✅" } catch { $Flag="❌" }
Pop-Location

# commit & push
$CommitMsg="feat(ops): add local run-e2e.ps1 and npm alias"
$CommitRes="Nothing to commit."
git add ops $FEPath\package.json | Out-Null
$st=git status --porcelain
if(-not [string]::IsNullOrWhiteSpace($st)){
  git commit -m $CommitMsg | Out-Null
  $CommitRes="Committed"
  git push origin main | Out-Null
}

$BackendOk=PortUp $BackendPort
$FrontendOk=($FEURL -ne $null)
"Backend: " + ($(if($BackendOk){"✅ (http://127.0.0.1:$BackendPort)"} else {"❌"})) | Out-Host
"Frontend: " + ($(if($FrontendOk){"✅ ($FEURL)"} else {"❌"})) | Out-Host
"Typecheck: " + ($(if($TypeOk){"✅"} else {"❌"})) | Out-Host
"Smoke: $Smoke" | Out-Host
"Templates flag test: $Flag" | Out-Host
"Commit: $CommitRes" | Out-Host
"Push: " + ($(if($CommitRes -ne "Nothing to commit."){"✅"} else {"(skipped)"})) | Out-Host
"Ready to push." | Out-Host
