#!/bin/bash
echo "Stopping Discord LLM Bot Docker services..."
docker compose -f docker/docker-compose.yml down
