Write-Output "Stopping e2e stack"
docker compose -f docker-compose.dev.yml down -v
