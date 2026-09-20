@echo off
echo Starting Discord LLM Bot with Docker Compose...
docker compose -f docker/docker-compose.yml up --build -d
pause