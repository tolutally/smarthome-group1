# 🏠 Complete Smart Home System Setup Guide

## 🎯 Overview

This guide will help you set up the complete Smart Home system with:
- ✅ **Backend API** (Flask + WebSocket)
- ✅ **Frontend Dashboard** (HTML + JavaScript)  
- ✅ **Database** (MongoDB + Redis)
- ✅ **Real-time Data** (MQTT + Sensor Simulation)
- ✅ **Demo Interface** (Advanced visualization)
- ✅ **Dummy Data** (7 days of realistic sensor data)

---

## 🚀 Quick Start (Automated)

### **Option 1: Complete Automated Setup**
```bash
cd backend
./start_complete_system.sh
```

This single command will:
- ✅ Start all database services (MongoDB, Redis, MQTT)
- ✅ Create environment configuration
- ✅ Install Python dependencies
- ✅ Seed database with dummy data
- ✅ Start backend API and sensor simulation
- ✅ Provide system health monitoring

---

## 🔧 Manual Setup (Step by Step)

### **Step 1: Start Database Services**
```bash
# MongoDB
docker run -d --name smart-home-mongodb -p 27017:27017 mongo:latest

# Redis (optional)
docker run -d --name smart-home-redis -p 6379:6379 redis:latest

# MQTT Broker
docker run -d --name smart-home-mqtt -p 1883:1883 eclipse-mosquitto:latest

# Wait for services to start
sleep 15
```

### **Step 2: Install Dependencies**
```bash
cd backend
pip3 install -r requirements.txt
```

### **Step 3: Configure Environment**
```bash
# Copy template and edit if needed
cp .env.template .env
```

### **Step 4: Seed Database with Dummy Data**
```bash
python3 seed_database.py
```

This will populate your database with:
- 📊 **~30,000 sensor readings** (7 days × 24 hours × 12 readings/hour × 5 rooms)
- 🚨 **~30 alerts** with various severity levels
- 👥 **2 sample users** with preferences
- ⚙️ **System settings** and thresholds

### **Step 5: Start Backend Services**
```bash
# Start main backend
python3 app.py &

# Start sensor simulation
python3 simulate_sensors.py &
```

### **Step 6: Access the System**
- **Frontend Dashboard**: http://localhost:5000
- **Demo UI**: `python3 demo_ui.py` then http://localhost:5001

---

## 📋 System Components

### **�� Backend API** (`app.py`)
- **Port**: 5000
- **Features**: REST API, WebSocket, MQTT integration
- **Endpoints**: `/api/sensors`, `/api/alerts`, `/api/userinfo`

### **🌐 Frontend Dashboard** (Served by backend)
- **URL**: http://localhost:5000
- **Features**: Real-time monitoring, alerts, settings
- **Authentication**: Google OAuth (optional)

### **🎛️ Demo UI** (`demo_ui.py`)
- **Port**: 5001
- **Features**: Advanced visualization, system testing
- **URL**: http://localhost:5001

### **💾 Databases**
- **MongoDB**: Sensor data, alerts, users (port 27017)
- **Redis**: Caching, statistics (port 6379)
- **MQTT**: Real-time messaging (port 1883)

### **🌡️ Sensor Simulation** (`simulate_sensors.py`)
- **Features**: Realistic sensor data generation
- **Rooms**: Living Room, Kitchen, Garage, Basement, Bedroom
- **Sensors**: Temperature, Humidity, CO Level, Battery

---

## 🔍 System Verification

### **Check System Status**
```bash
python3 check_system_status.py
```

### **Test Individual Components**

#### **Database Connection**
```bash
# MongoDB
python3 -c "from pymongo import MongoClient; print('✅ MongoDB' if MongoClient('mongodb://localhost:27017/').admin.command('ismaster') else '❌ MongoDB')"

# Redis
python3 -c "import redis; print('✅ Redis' if redis.Redis().ping() else '❌ Redis')"
```

#### **Backend API**
```bash
# Health check
curl http://localhost:5000/api/userinfo

# Sensor data
curl http://localhost:5000/api/sensors
```

#### **Database Data**
```bash
# Check sensor data count
python3 -c "from pymongo import MongoClient; db = MongoClient().smarthome; print(f'Sensor readings: {db.sensor_data.count_documents({}):,}')"
```

---

## 📊 Database Schema

### **Sensor Data Collection**
```json
{
  "sensor_id": "LIVING_ROOM_001",
  "room": "Living Room",
  "temperature": 22.5,
  "humidity": 45.0,
  "co_level": 1.2,
  "battery_level": 85,
  "signal_strength": -45,
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "normal"
}
```

### **Alerts Collection**
```json
{
  "id": "alert_1705312200_456",
  "type": "HIGH_TEMPERATURE",
  "severity": "WARNING",
  "room": "Kitchen",
  "sensor_id": "KITCHEN_001",
  "message": "High temperature detected in Kitchen",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "ACTIVE",
  "acknowledged": false,
  "threshold_value": 30.0,
  "current_value": 35.2
}
```

---

## 🎮 Usage Examples

### **1. View Real-time Dashboard**
1. Open http://localhost:5000
2. Authenticate (if Google OAuth configured)
3. Click "Connect" to start real-time updates
4. Watch sensor data and alerts update live

### **2. Use Advanced Demo UI**
1. Run `python3 demo_ui.py`
2. Open http://localhost:5001
3. Click "▶️ Start Demo" for simulation
4. Explore interactive panels and controls

### **3. Trigger Manual Alert**
```bash
curl -X POST http://localhost:5000/api/sensors/data \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "TEST_001",
    "room": "Kitchen",
    "temperature": 40.0,
    "humidity": 60.0,
    "co_level": 8.5,
    "battery_level": 10,
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'
```

### **4. Query Historical Data**
```bash
# Get recent sensor data
curl "http://localhost:5000/api/sensors?limit=10"

# Get alerts
curl "http://localhost:5000/api/alerts"
```

---

## 🔧 Configuration Options

### **Environment Variables** (`.env`)
```env
# Database
MONGODB_URI=mongodb://localhost:27017/smarthome
REDIS_URL=redis://localhost:6379/0

# MQTT
MQTT_HOST=localhost
MQTT_PORT=1883

# Security
SECRET_KEY=your-secret-key

# Optional: Notifications
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### **Alert Thresholds** (Stored in database)
```json
{
  "temperature": {"min": 10, "max": 30},
  "humidity": {"min": 30, "max": 70},
  "co_level": {"max": 5.0},
  "battery_level": {"min": 20}
}
```

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **Port Already in Use**
```bash
# Find what's using the port
lsof -i :5000

# Kill the process
kill -9 <PID>
```

#### **Database Connection Failed**
```bash
# Check if Docker containers are running
docker ps

# Restart containers
docker restart smart-home-mongodb smart-home-redis smart-home-mqtt
```

#### **No Sensor Data**
```bash
# Check if simulation is running
ps aux | grep simulate_sensors

# Restart sensor simulation
python3 simulate_sensors.py &
```

#### **Frontend Won't Load**
```bash
# Check backend is running
curl http://localhost:5000/api/userinfo

# Check if frontend files exist
ls -la ../frontend/index.html
```

### **Logs and Debugging**
```bash
# View backend logs
tail -f app.log

# Monitor MQTT messages
docker exec -it smart-home-mqtt mosquitto_sub -h localhost -t "#" -v

# Check MongoDB data
docker exec -it smart-home-mongodb mongosh
use smarthome
db.sensor_data.find().limit(5)
```

---

## 📈 Performance & Monitoring

### **System Resources**
- **MongoDB**: ~50MB for 30K sensor records
- **Redis**: ~10MB for cached data
- **Backend**: ~50MB RAM usage
- **Docker**: ~200MB total for all containers

### **Data Throughput**
- **Sensor readings**: 12 per hour per room (5 rooms = 60/hour)
- **MQTT messages**: Real-time as generated
- **WebSocket updates**: Every 3-5 seconds
- **Database writes**: Batch insertions for performance

### **Health Monitoring**
```bash
# Continuous monitoring
./start_complete_system.sh  # Includes health monitoring

# Manual status check
python3 check_system_status.py
```

---

## 🚀 Production Considerations

### **Security**
- [ ] Configure MongoDB authentication
- [ ] Set up Redis password protection
- [ ] Use HTTPS for frontend
- [ ] Configure MQTT authentication
- [ ] Set up proper API authentication

### **Scalability**
- [ ] MongoDB sharding for large datasets
- [ ] Redis clustering for high availability
- [ ] Load balancing for multiple backend instances
- [ ] MQTT cluster for high throughput

### **Deployment**
- [ ] Docker Compose for container orchestration
- [ ] Kubernetes for cloud deployment
- [ ] CI/CD pipeline for automated deployment
- [ ] Monitoring and alerting systems

---

## 🎉 Success Checklist

✅ **Database services running** (MongoDB, Redis, MQTT)  
✅ **Backend API responding** (port 5000)  
✅ **Frontend loading** (http://localhost:5000)  
✅ **Real-time data flowing** (WebSocket connection)  
✅ **Sensor simulation active** (MQTT messages)  
✅ **Database populated** (30K+ sensor records)  
✅ **Alerts working** (threshold monitoring)  
✅ **Demo UI functional** (port 5001)  

### **System is ready for:**
- 🎯 **Development and testing**
- 📊 **Data analysis and visualization**  
- 🎪 **Demonstrations and presentations**
- 🏗️ **Further feature development**
- 🚀 **Production deployment preparation**

---

## 📞 Quick Reference

### **Essential Commands**
```bash
# Start complete system
./start_complete_system.sh

# Check system status  
python3 check_system_status.py

# Seed database
python3 seed_database.py

# Start demo UI
python3 demo_ui.py

# View frontend
open http://localhost:5000
```

### **Key URLs**
- **Frontend**: http://localhost:5000
- **Demo UI**: http://localhost:5001
- **API Health**: http://localhost:5000/api/userinfo
- **Sensor Data**: http://localhost:5000/api/sensors

### **Support**
- **Documentation**: `README.md`, `TESTING_README.md`, `DEMO_UI_GUIDE.md`
- **Status Check**: `python3 check_system_status.py`
- **Logs**: Monitor `app.py` output and Docker container logs

**🏠 Your Smart Home System is now fully operational!** 🎉
