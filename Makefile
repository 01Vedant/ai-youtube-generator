.PHONY: help up down logs clean smoke build-images restart

help:
	@echo "Bhakti Video Generator - Development Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make up              Start all services (docker-compose up -d)"
	@echo "  make down            Stop and remove all services"
	@echo "  make logs            Tail logs from all services"
	@echo "  make restart         Restart all services"
	@echo "  make clean           Remove volumes, containers, networks"
	@echo "  make build-images    Build Docker images locally"
	@echo "  make smoke           Run smoke test against running services"
	@echo ""

up:
	@echo "Starting Bhakti Video Generator services..."
	docker-compose up -d
	@echo "Services started. Check status with 'make logs'"
	@echo "Frontend: http://localhost"
	@echo "Backend: http://localhost:8000"
	@echo "MinIO console: http://localhost:9001 (bhakti/bhakti123)"

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	@echo "Tailing logs from all services (Ctrl+C to exit)..."
	docker-compose logs -f

restart:
	@echo "Restarting all services..."
	docker-compose restart
	@echo "Services restarted."

clean:
	@echo "WARNING: This will remove all containers, volumes, and networks"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v
	@echo "Clean complete."

build-images:
	@echo "Building Docker images..."
	docker-compose build
	@echo "Build complete."

smoke:
	@echo "Running smoke test..."
	@echo ""
	@echo "1. Checking backend health..."
	@for i in 1 2 3 4 5; do \
		if curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then \
			echo "✓ Backend health check passed"; \
			break; \
		fi; \
		if [ $$i -lt 5 ]; then echo "  Retry $$i/5..."; sleep 2; fi; \
	done
	@echo ""
	@echo "2. Checking frontend health..."
	@for i in 1 2 3 4 5; do \
		if curl -sf http://localhost/healthz > /dev/null 2>&1; then \
			echo "✓ Frontend health check passed"; \
			break; \
		fi; \
		if [ $$i -lt 5 ]; then echo "  Retry $$i/5..."; sleep 2; fi; \
	done
	@echo ""
	@echo "3. Checking MinIO connectivity..."
	@docker-compose exec -T minio mc ls bhakti > /dev/null 2>&1 && echo "✓ MinIO bucket accessible" || echo "✗ MinIO check failed"
	@echo ""
	@echo "Smoke test complete!"

.DEFAULT_GOAL := help
