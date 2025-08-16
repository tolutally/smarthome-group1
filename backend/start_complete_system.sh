#!/bin/bash

echo "🏠 Starting Complete Smart Home System with Database"
echo "=================================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Check prerequisites
echo "�� Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists docker; then
    echo "❌ Docker is required but not installed"
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Prerequisites satisfied"
echo ""

# Check if ports are available
echo "🔌 Checking port availability..."
PORTS_NEEDED=(5000 5001 27017 6379 1883)
PORTS_IN_USE=()

for port in "${PORTS_NEEDED[@]}"; do
    if port_in_use $port; then
        PORTS_IN_USE+=($port)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    echo "⚠️  Warning: The following ports are in use: ${PORTS_IN_USE[*]}"
    echo "   This might cause conflicts. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "✅ Port check completed"
echo ""

# Start database services
echo "📊 Starting database services..."

# Stop existing containers (if any)
docker stop smart-home-mongodb smart-home-redis smart-home-mqtt >/dev/null 2>&1
docker rm smart-home-mongodb smart-home-redis smart-home-mqtt >/dev/null 2>&1

# Start MongoDB
echo "   Starting MongoDB..."
docker run -d \
  --name smart-home-mongodb \
  -p 27017:27017 \
  -v smart-home-mongodb-data:/data/db \
  mongo:latest >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ MongoDB started on port 27017"
else
    echo "   ❌ Failed to start MongoDB"
    exit 1
fi

# Start Redis
echo "   Starting Redis..."
docker run -d \
  --name smart-home-redis \
  -p 6379:6379 \
  -v smart-home-redis-data:/data \
  redis:latest redis-server --appendonly yes >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ Redis started on port 6379"
else
    echo "   ⚠️  Redis failed to start (optional service)"
fi

# Start MQTT Broker
echo "   Starting MQTT Broker..."
docker run -d \
  --name smart-home-mqtt \
  -p 1883:1883 \
  -p 9001:9001 \
  eclipse-mosquitto:latest >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ MQTT Broker started on port 1883"
else
    echo "   ⚠️  MQTT Broker failed to start (sensor simulation will be affected)"
fi

# Wait for services to be ready
echo ""
echo "⏳ Waiting for database services to initialize..."
sleep 15

# Test database connections
echo "🔗 Testing database connections..."

# Test MongoDB
python3 -c "
from pymongo import MongoClient
try:
    client = MongoClient('mongodb://localhost:27017/')
    client.admin.command('ismaster')
    print('   ✅ MongoDB connection successful')
except Exception as e:
    print(f'   ❌ MongoDB connection failed: {e}')
    exit(1)
" || exit 1

# Test Redis (optional)
python3 -c "
import redis
try:
    client = redis.Redis(host='localhost', port=6379, db=0)
    client.ping()
    print('   ✅ Redis connection successful')
except Exception:
    print('   ⚠️  Redis connection failed (optional)')
" 2>/dev/null

echo ""

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment configuration..."
    cat > .env << 'ENVEOF'
# Smart Home System Environment Configuration

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/smarthome
REDIS_URL=redis://localhost:6379/0

# MQTT Configuration
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC=smarthome/sensors/+/data

# Flask Configuration
SECRET_KEY=smart-home-secret-key-$(date +%s)
FLASK_ENV=development

# Optional: Google OAuth (leave empty to disable)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Optional: Notification Settings
EMAIL_USER=
EMAIL_PASSWORD=
VONAGE_API_KEY=
VONAGE_API_SECRET=
FCM_SERVER_KEY=
WEBHOOK_URLS=
DEFAULT_NOTIFICATION_EMAIL=
DEFAULT_NOTIFICATION_PHONE=
ENVEOF
    echo "   ✅ .env file created with default configuration"
else
    echo "📝 Using existing .env configuration"
fi

echo ""

# Check and install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ Dependencies installed successfully"
    else
        echo "   ⚠️  Some dependencies may have failed to install"
    fi
else
    echo "   ⚠️  requirements.txt not found"
fi

echo ""

# Seed database with dummy data
echo "🌱 Seeding database with dummy data..."
echo "   This will populate the database with 7 days of realistic sensor data"
echo "   Continue with database seeding? (Y/n)"
read -r seed_response
if [[ ! "$seed_response" =~ ^[Nn]$ ]]; then
    if [ -f seed_database.py ]; then
        python3 seed_database.py
        if [ $? -eq 0 ]; then
            echo "   ✅ Database seeding completed successfully"
        else
            echo "   ⚠️  Database seeding completed with warnings"
        fi
    else
        echo "   ❌ seed_database.py not found"
    fi
else
    echo "   ⏭️  Skipping database seeding"
fi

echo ""

# Start backend services
echo "🔄 Starting backend services..."

# Kill any existing processes on required ports
if port_in_use 5000; then
    echo "   Stopping existing process on port 5000..."
    lsof -ti:5000 | xargs kill -9 >/dev/null 2>&1
fi

if port_in_use 5001; then
    echo "   Stopping existing process on port 5001..."
    lsof -ti:5001 | xargs kill -9 >/dev/null 2>&1
fi

# Start main backend
echo "   Starting main backend server..."
python3 app.py &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 5

# Test backend
echo "   Testing backend connection..."
if curl -s http://localhost:5000/api/userinfo >/dev/null 2>&1; then
    echo "   ✅ Backend server is running on http://localhost:5000"
else
    echo "   ⚠️  Backend server may not be responding"
fi

# Start sensor simulation
echo "   Starting sensor simulation..."
if [ -f simulate_sensors.py ]; then
    python3 simulate_sensors.py &
    SENSOR_PID=$!
    echo "   Sensor simulation PID: $SENSOR_PID"
    echo "   ✅ Sensor simulation started"
else
    echo "   ⚠️  simulate_sensors.py not found"
    SENSOR_PID=""
fi

echo ""

# System ready message
echo "🎉 Smart Home System Started Successfully!"
echo "========================================"
echo ""
echo "🌐 Frontend Dashboard:    http://localhost:5000"
echo "🎛️  Demo UI (Advanced):    http://localhost:5001 (run separately)"
echo "📊 Database:              MongoDB on localhost:27017"
echo "📦 Cache:                 Redis on localhost:6379"
echo "📡 MQTT Broker:           localhost:1883"
echo ""
echo "🎮 Quick Actions:"
echo "   • Open frontend:       open http://localhost:5000"
echo "   • Start demo UI:       python3 demo_ui.py"
echo "   • View backend logs:   tail -f app.log"
echo "   • Stop system:         kill $BACKEND_PID $SENSOR_PID"
echo ""
echo "📋 Database Status:"
python3 -c "
from pymongo import MongoClient
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client.smarthome
    sensor_count = db.sensor_data.count_documents({})
    alert_count = db.alerts.count_documents({})
    print(f'   📊 Sensor readings: {sensor_count:,}')
    print(f'   🚨 Total alerts: {alert_count}')
    print(f'   🟢 Active alerts: {db.alerts.count_documents({\"status\": \"ACTIVE\"})}')
except:
    print('   ❌ Could not connect to database')
"
echo ""
echo "🛑 To stop the system:"
echo "   kill $BACKEND_PID $SENSOR_PID"
echo "   docker stop smart-home-mongodb smart-home-redis smart-home-mqtt"
echo ""
echo "💡 Tip: Open http://localhost:5000 in your browser to see the dashboard!"

# Save PIDs for later cleanup
cat > .system_pids << PIDEOF
BACKEND_PID=$BACKEND_PID
SENSOR_PID=$SENSOR_PID
PIDEOF

# Keep script running and monitor processes
echo "🔍 Monitoring system health... (Press Ctrl+C to stop)"
echo ""

trap 'echo ""; echo "🛑 Stopping Smart Home System..."; kill $BACKEND_PID $SENSOR_PID 2>/dev/null; docker stop smart-home-mongodb smart-home-redis smart-home-mqtt >/dev/null 2>&1; echo "✅ System stopped"; exit 0' INT

# Monitor loop
while true; do
    sleep 30
    
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "⚠️  Backend process stopped unexpectedly"
        break
    fi
    
    # Check if sensor simulation is still running
    if [ -n "$SENSOR_PID" ] && ! kill -0 $SENSOR_PID 2>/dev/null; then
        echo "⚠️  Sensor simulation stopped unexpectedly"
    fi
    
    echo "💚 System running healthy at $(date '+%H:%M:%S')"
done
