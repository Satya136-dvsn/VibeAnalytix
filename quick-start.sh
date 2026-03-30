#!/bin/bash
# Quick start script for VibeAnalytix development

set -e

echo "🚀 VibeAnalytix Setup"
echo "===================="

# Check for required commands
command -v docker &> /dev/null || { echo "❌ Docker is not installed"; exit 1; }
command -v docker-compose &> /dev/null || { echo "❌ Docker Compose is not installed"; exit 1; }

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Update .env with your OpenAI API key before continuing"
    exit 1
fi

# Start services
echo "🐳 Starting Docker Compose services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "📍 Access points:"
    echo "   Frontend: http://localhost:3000"
    echo "   API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Open http://localhost:3000 in your browser"
    echo "   2. Create an account"
    echo "   3. Submit a GitHub repository or ZIP file"
    echo ""
    echo "📊 Monitor progress:"
    echo "   docker-compose logs -f api"
    echo "   docker-compose logs -f worker"
else
    echo "❌ Failed to start services"
    docker-compose logs
    exit 1
fi
