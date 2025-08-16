#!/bin/bash

# Smart Home Backend - Service Startup Script

echo "🏠 Starting Smart Home Backend Services..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker to run the services."
    exit 1
fi

# Function to check if a container is running
check_container() {
    docker ps | grep -q "$1"
}

# Start MongoDB
echo "📊 Starting MongoDB..."
if check_container "mongodb"; then
    echo "✅ MongoDB is already running"
else
    docker run -d -p 27017:27017 --name mongodb \
        -e MONGO_INITDB_DATABASE=smarthome_db \
        mongo:latest
    echo "✅ MongoDB started on port 27017"
fi

# Start Redis
echo "⚡ Starting Redis..."
if check_container "redis"; then
    echo "✅ Redis is already running"
else
    docker run -d -p 6379:6379 --name redis redis:latest
    echo "✅ Redis started on port 6379"
fi

# Start MQTT Broker (Mosquitto)
echo "📡 Starting MQTT Broker..."
if check_container "mosquitto"; then
    echo "✅ MQTT Broker is already running"
else
    docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto:latest
    echo "✅ MQTT Broker started on port 1883"
fi

# Wait a moment for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 3

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from env.example..."
    cp env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "🎉 All services are ready!"
echo ""
echo "📋 Service Status:"
echo "   🔘 MongoDB:     http://localhost:27017"
echo "   🔘 Redis:       redis://localhost:6379"
echo "   🔘 MQTT Broker: mqtt://localhost:1883"
echo ""
echo "🚀 To start the backend:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "📊 To start sensor simulation:"
echo "   python simulate_sensors.py"
echo ""
echo "🛑 To stop all services:"
echo "   docker stop mongodb redis mosquitto"
echo "   docker rm mongodb redis mosquitto" 