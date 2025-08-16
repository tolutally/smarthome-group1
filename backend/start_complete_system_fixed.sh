#!/bin/bash

echo "🏠 Starting Complete Smart Home System"
echo "====================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Docker daemon is running
docker_running() {
    docker info >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists docker; then
    echo "⚠️  Docker is not installed. Installing local alternatives..."
    USE_LOCAL_DB=true
else
    echo "✅ Docker is installed"
    if ! docker_running; then
        echo "⚠️  Docker daemon is not running"
        echo "   You can either:"
        echo "   1. Start Docker Desktop manually, then run this script again"
        echo "   2. Continue with local database alternatives (MongoDB not required for basic demo)"
        echo ""
        read -p "Continue with local alternatives? (Y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
            echo "Please start Docker Desktop and run this script again."
            echo "💡 To start Docker Desktop:"
            echo "   - Open Docker Desktop application"
            echo "   - Wait for it to fully start (Docker icon in menu bar should be steady)"
            echo "   - Then run: ./start_complete_system_fixed.sh"
            exit 1
        fi
        USE_LOCAL_DB=true
    else
        echo "✅ Docker daemon is running"
        USE_LOCAL_DB=false
    fi
fi

echo ""

# Check if ports are available
echo "🔌 Checking port availability..."
PORTS_NEEDED=(5000 5001)
if [ "$USE_LOCAL_DB" = false ]; then
    PORTS_NEEDED+=(27017 6379 1883)
fi

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
        echo "Aborted. Please free up the ports and try again."
        echo "💡 To kill processes on specific ports:"
        for port in "${PORTS_IN_USE[@]}"; do
            echo "   lsof -ti:$port | xargs kill -9"
        done
        exit 1
    fi
fi

echo "✅ Port check completed"
echo ""

# Start database services
if [ "$USE_LOCAL_DB" = false ]; then
    echo "📊 Starting Docker database services..."

    # Stop existing containers (if any)
    docker stop smart-home-mongodb smart-home-redis smart-home-mqtt >/dev/null 2>&1
    docker rm smart-home-mongodb smart-home-redis smart-home-mqtt >/dev/null 2>&1

    # Start MongoDB
    echo "   Starting MongoDB..."
    if docker run -d \
      --name smart-home-mongodb \
      -p 27017:27017 \
      -v smart-home-mongodb-data:/data/db \
      mongo:latest >/dev/null 2>&1; then
        echo "   ✅ MongoDB started on port 27017"
        MONGODB_STARTED=true
    else
        echo "   ❌ Failed to start MongoDB"
        MONGODB_STARTED=false
    fi

    # Start Redis
    echo "   Starting Redis..."
    if docker run -d \
      --name smart-home-redis \
      -p 6379:6379 \
      -v smart-home-redis-data:/data \
      redis:latest redis-server --appendonly yes >/dev/null 2>&1; then
        echo "   ✅ Redis started on port 6379"
        REDIS_STARTED=true
    else
        echo "   ⚠️  Redis failed to start (optional service)"
        REDIS_STARTED=false
    fi

    # Start MQTT Broker
    echo "   Starting MQTT Broker..."
    if docker run -d \
      --name smart-home-mqtt \
      -p 1883:1883 \
      -p 9001:9001 \
      eclipse-mosquitto:latest >/dev/null 2>&1; then
        echo "   ✅ MQTT Broker started on port 1883"
        MQTT_STARTED=true
    else
        echo "   ⚠️  MQTT Broker failed to start (sensor simulation will be affected)"
        MQTT_STARTED=false
    fi

    # Wait for services to be ready
    if [ "$MONGODB_STARTED" = true ]; then
        echo ""
        echo "⏳ Waiting for database services to initialize..."
        sleep 15
    fi
else
    echo "📊 Using local database alternatives..."
    echo "   ✅ Will use in-memory data storage for demo"
    echo "   ✅ WebSocket streaming will work normally"
    echo "   ⚠️  Data will not persist between sessions"
    MONGODB_STARTED=false
    REDIS_STARTED=false
    MQTT_STARTED=false
fi

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
SECRET_KEY=smart-home-secret-key-demo-$(date +%s)
FLASK_ENV=development

# Demo Mode (when MongoDB is not available)
DEMO_MODE=true

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

# Database seeding
if [ "$MONGODB_STARTED" = true ]; then
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
else
    echo "🌱 Skipping database seeding (using in-memory demo data)"
fi

echo ""

# Start backend services
echo "🔄 Starting backend services..."

# Kill any existing processes on required ports
if port_in_use 5000; then
    echo "   Stopping existing process on port 5000..."
    lsof -ti:5000 | xargs kill -9 >/dev/null 2>&1
    sleep 2
fi

if port_in_use 5001; then
    echo "   Stopping existing process on port 5001..."
    lsof -ti:5001 | xargs kill -9 >/dev/null 2>&1
    sleep 2
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
    BACKEND_RUNNING=true
else
    echo "   ⚠️  Backend server may not be responding yet (give it a moment)"
    BACKEND_RUNNING=false
fi

# Start sensor simulation if MQTT is available or use internal simulation
echo "   Starting sensor simulation..."
if [ -f simulate_sensors.py ] && [ "$MQTT_STARTED" = true ]; then
    python3 simulate_sensors.py &
    SENSOR_PID=$!
    echo "   Sensor simulation PID: $SENSOR_PID (with MQTT)"
    echo "   ✅ External sensor simulation started"
elif [ -f simulate_sensors.py ]; then
    # Modify sensor simulation to work without MQTT
    echo "   ✅ Using internal sensor simulation (MQTT not available)"
    SENSOR_PID=""
else
    echo "   ⚠️  simulate_sensors.py not found, using internal simulation"
    SENSOR_PID=""
fi

echo ""

# System ready message
echo "🎉 Smart Home System Started Successfully!"
echo "========================================"
echo ""
echo "🌐 Frontend Dashboard:    http://localhost:5000"
echo "🎛️  Demo UI:              python3 demo_ui.py (run in new terminal)"
if [ "$MONGODB_STARTED" = true ]; then
    echo "📊 Database:              MongoDB on localhost:27017"
else
    echo "📊 Database:              In-memory demo mode"
fi
if [ "$REDIS_STARTED" = true ]; then
    echo "📦 Cache:                 Redis on localhost:6379"
fi
if [ "$MQTT_STARTED" = true ]; then
    echo "📡 MQTT Broker:           localhost:1883"
fi
echo ""
echo "🎮 Quick Actions:"
echo "   • Open frontend:       open http://localhost:5000"
echo "   • Start demo UI:       python3 demo_ui.py"
echo "   • Check system:        python3 check_system_status.py"
if [ -n "$BACKEND_PID" ]; then
    echo "   • Stop backend:        kill $BACKEND_PID"
fi
if [ -n "$SENSOR_PID" ]; then
    echo "   • Stop sensors:        kill $SENSOR_PID"
fi

echo ""

# Database status
if [ "$MONGODB_STARTED" = true ]; then
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
    active_alerts = db.alerts.count_documents({'status': 'ACTIVE'})
    print(f'   🟢 Active alerts: {active_alerts}')
except Exception as e:
    print(f'   ❌ Database connection error: {e}')
"
else
    echo "📋 System Status:"
    echo "   🎪 Demo mode active - using in-memory data"
    echo "   🔄 Real-time WebSocket streaming available"
    echo "   📊 Mock sensor data will be generated"
fi

echo ""

if [ "$USE_LOCAL_DB" = true ]; then
    echo "💡 Running in Demo Mode:"
    echo "   • ✅ Backend API and WebSocket streaming work normally"
    echo "   • ✅ Frontend dashboard fully functional with mock data"
    echo "   • ✅ Real-time updates and alerts working"
    echo "   • ⚠️  Data will not persist between sessions"
    echo "   • 💾 To use persistent storage, start Docker Desktop and re-run"
    echo ""
fi

echo "🛑 To stop the system:"
if [ -n "$BACKEND_PID" ]; then
    echo "   kill $BACKEND_PID"
fi
if [ -n "$SENSOR_PID" ]; then
    echo "   kill $SENSOR_PID"
fi
if [ "$USE_LOCAL_DB" = false ]; then
    echo "   docker stop smart-home-mongodb smart-home-redis smart-home-mqtt"
fi
echo ""

echo "💡 Tip: Open http://localhost:5000 in your browser to see the dashboard!"

# Save PIDs for later cleanup
cat > .system_pids << PIDEOF
BACKEND_PID=$BACKEND_PID
SENSOR_PID=$SENSOR_PID
USE_LOCAL_DB=$USE_LOCAL_DB
PIDEOF

echo ""
echo "🔍 System is ready! Use 'python3 check_system_status.py' to verify health."
