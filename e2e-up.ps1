$Env:SIMULATE_RENDER = "1"
$Env:FEATURE_TEMPLATES_MARKETPLACE = "1"
$Env:APP_ENV = "dev"
Write-Output "Starting e2e stack with SIMULATE_RENDER=1 and marketplace flag ON"
docker compose -f docker-compose.dev.yml up -d --build
