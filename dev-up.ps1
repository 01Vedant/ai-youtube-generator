docker compose -f docker-compose.dev.yml up --build -d
Write-Host "API → http://localhost:8000/docs"
Write-Host "MinIO console → http://localhost:9001 (minioadmin / minioadmin)"
