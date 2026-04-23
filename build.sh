#!/usr/bin/env bash
# Render build script - runs before app starts

echo "🔧 Installing dependencies..."
pip install -r requirements.txt

echo "🗄️  Setting up PostgreSQL database..."
python setup_postgresql_render.py

echo "✅ Build complete!"
