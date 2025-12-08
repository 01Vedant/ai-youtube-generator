param(
  [string]$ApiBase = "http://127.0.0.1:8000"
)

Write-Host "Public smoke: robots.txt" -ForegroundColor Cyan
$robots = Invoke-WebRequest -Uri "$ApiBase/public/robots.txt" -Method Get -ErrorAction Stop
Write-Host "robots status: $($robots.StatusCode)"

Write-Host "Public smoke: sitemap.xml" -ForegroundColor Cyan
$sitemap = Invoke-WebRequest -Uri "$ApiBase/public/sitemap.xml" -Method Get -ErrorAction Stop
Write-Host "sitemap status: $($sitemap.StatusCode)"

Write-Host "Public smoke: waitlist join" -ForegroundColor Cyan
$email = "smoke_$([Guid]::NewGuid().ToString('N'))@example.com"
$body = @{ email = $email; source = "smoke" } | ConvertTo-Json
$wl = Invoke-WebRequest -Uri "$ApiBase/public/waitlist" -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
Write-Host "waitlist status: $($wl.StatusCode)"
Write-Host "Done." -ForegroundColor Green