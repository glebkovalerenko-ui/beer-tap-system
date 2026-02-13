#!/bin/bash

# This script initializes the database by applying Alembic migrations.

echo "Running Alembic migrations to initialize the database..."
docker-compose exec beer_backend_api alembic upgrade head

echo "Database initialization complete."