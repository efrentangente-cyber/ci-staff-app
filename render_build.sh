#!/usr/bin/env bash
# Render build script - runs before app starts

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating PostgreSQL tables..."
python create_missing_tables_postgresql.py

echo "Build complete!"
