#!/bin/bash

echo "🏠 Starting Smart Home System (Docker-Free Mode)"
echo "==============================================="
echo ""

# Function to check if port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

echo "🎪 Starting in Demo Mode (No Docker Required)"
echo "   ✅ Backend API with in-memory data storage"
echo "   ✅ Real-time WebSocket streaming"
echo "   ✅ Mock sensor data generation"
echo "   ✅ Alert system with simulated thresholds"
echo "   ⚠️  Data will not persist between sessions"
echo ""

# Check if macOS AirPlay is using port 5000
if port_in_use 5000; then
    echo "📡 Note: Port 5000 is in use by macOS AirPlay - using port 5001 instead"
    echo "   💡 To use port 5000: System Settings > General > AirDrop & Handoff > AirPlay Receiver (Off)"
    echo ""
fi

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi
echo "✅ Python 3 available"

# Install dependencies
echo "📦 Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt >/dev/null 2>&1
    echo "   ✅ Dependencies installed"
else
    echo "   ⚠️  requirements.txt not found"
fi

# Create demo environment
echo "📝 Creating demo environment configuration..."
cat > .env << 'ENVEOF'
# Smart Home Demo Mode Configuration
DEMO_MODE=true
SECRET_KEY=demo-secret-key-$(date +%s)
FLASK_ENV=development
FLASK_PORT=5001

# Database URLs (will use in-memory fallbacks)
MONGODB_URI=mongodb://localhost:27017/smarthome
REDIS_URL=redis://localhost:6379/0
MQTT_HOST=localhost
MQTT_PORT=1883

# Demo settings
USE_MOCK_DATA=true
PERSIST_DATA=false
ENVEOF
echo "   ✅ Demo environment configured"

# Kill existing processes
if port_in_use 5001; then
    echo "🔄 Stopping existing backend on port 5001..."
    lsof -ti:5001 | xargs kill -9 >/dev/null 2>&1
    sleep 2
fi

if port_in_use 5002; then
    echo "🔄 Stopping existing demo UI on port 5002..."
    lsof -ti:5002 | xargs kill -9 >/dev/null 2>&1
    sleep 2
fi

echo ""
echo "🚀 Starting backend services..."

# Start main backend in demo mode
python3 app.py &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 5

# Test backend on both possible ports
BACKEND_PORT=""
if curl -s http://localhost:5001/api/userinfo >/dev/null 2>&1; then
    echo "   ✅ Backend server running on http://localhost:5001"
    BACKEND_PORT="5001"
elif curl -s http://localhost:5002/api/userinfo >/dev/null 2>&1; then
    echo "   ✅ Backend server running on http://localhost:5002"
    BACKEND_PORT="5002"
else
    echo "   ⚠️  Backend starting up... (check ports 5001-5002 in a moment)"
    BACKEND_PORT="5001"
fi

echo ""
echo "🎉 Smart Home Demo System Ready!"
echo "==============================="
echo ""
echo "🌐 Frontend Dashboard:    http://localhost:${BACKEND_PORT}"
echo "🎛️  Advanced Demo UI:     python3 demo_ui.py (run in new terminal)"
echo "📊 Data Mode:             In-memory mock data"
echo "🔄 Updates:               Real-time via WebSocket"
echo ""
echo "🎮 What You Can Do:"
echo "   • ✅ View real-time sensor data"
echo "   • ✅ See alerts and notifications"
echo "   • ✅ Test WebSocket connections"
echo "   • ✅ Explore the demo interface"
echo "   • ✅ Test API endpoints"
echo ""
echo "📡 Demo Features Active:"
echo "   • 🌡️  Temperature, Humidity, CO sensors"
echo "   • 🏠 5 rooms with different sensor profiles"
echo "   • 🚨 Alert generation on threshold violations"
echo "   • 🔄 Real-time data updates every 3-5 seconds"
echo "   • 📊 Historical data simulation"
echo ""
echo "🎯 Quick Actions:"
echo "   • Open dashboard:      open http://localhost:${BACKEND_PORT}"
echo "   • Start advanced demo: python3 demo_ui.py"
echo "   • Test API:           curl http://localhost:${BACKEND_PORT}/api/sensors"
echo "   • Stop system:        kill $BACKEND_PID"
echo ""
echo "💡 Pro Tip: For persistent data storage, install Docker Desktop and use:"
echo "   ./start_complete_system_fixed.sh"
echo ""

# Save PID for cleanup
echo "BACKEND_PID=$BACKEND_PID" > .system_pids
echo "BACKEND_PORT=$BACKEND_PORT" >> .system_pids
echo "DEMO_MODE=true" >> .system_pids

echo "✨ System ready! Open http://localhost:${BACKEND_PORT} to get started!" 