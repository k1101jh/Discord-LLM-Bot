#!/bin/bash
echo "Starting Discord LLM Bot Docker services..."
docker compose -f docker/docker-compose.yml up --build -d
