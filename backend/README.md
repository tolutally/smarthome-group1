# Smart Home Backend Service

Flask-based backend service for the smart home monitoring system with real-time sensor data processing, MQTT integration, and alert management.

## Features

- **Real-time Sensor Data Processing**: Handles temperature, humidity, and CO sensor readings
- **MQTT Integration**: Subscribes to sensor data via MQTT broker
- **MongoDB Storage**: Persistent storage with optimized indexing
- **Redis Caching**: Fast data retrieval and statistics caching
- **WebSocket Support**: Real-time updates to connected clients
- **Alert System**: Threshold-based alerts with severity levels
- **Sensor Buffering**: Offline data buffering with automatic forwarding

## Architecture

```
MQTT Sensors → MQTT Broker → Flask Backend → MongoDB + Redis → WebSocket → Frontend
                                    ↓
                              Alert System → Notifications
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend/
pip install -r requirements.txt
```

### 2. Setup Environment

```bash
cp env.example .env
# Edit .env with your configuration
```

### 3. Start Services

**MongoDB** (using Docker):
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

**Redis** (using Docker):
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

**MQTT Broker** (using Docker):
```bash
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto:latest
```

### 4. Start Backend

```bash
python app.py
```

### 5. Start Sensor Simulation

```bash
python simulate_sensors.py
```

## API Endpoints

### Sensor Data
- `GET /api/sensors` - Get sensor data with optional filtering
- `GET /api/sensor-stats` - Get aggregated statistics

### Alerts
- `GET /api/alerts` - Get alerts with optional filtering

### Parameters
- `room`: Filter by room name
- `type`: Filter by sensor type (temperature, humidity, co)
- `limit`: Maximum number of records (default: 100)

## WebSocket Events

### Client → Server
- `connect` - Client connection
- `disconnect` - Client disconnection

### Server → Client
- `connected` - Connection confirmation
- `sensor_data` - Real-time sensor readings
- `new_alert` - Alert notifications
- `alert_acknowledged` - Alert acknowledgments
- `alert_resolved` - Alert resolutions

## Sensor Types & Thresholds

| Sensor | Min | Max | Unit | Critical Levels |
|--------|-----|-----|------|-----------------|
| Temperature | 18°C | 30°C | °C | < 10°C or > 35°C |
| Humidity | 30% | 70% | % | < 20% or > 80% |
| CO Level | 0 ppm | 50 ppm | ppm | > 100 ppm |

## MongoDB Schema

### SensorData Collection
```javascript
{
  sensor_id: String,
  sensor_type: String, // 'temperature', 'humidity', 'co'
  value: Number,
  room: String,
  unit: String,
  timestamp: Date,
  created_at: Date,
  status: String
}
```

### Alerts Collection
```javascript
{
  alert_id: String,
  sensor_id: String,
  room: String,
  sensor_type: String,
  alert_type: String,
  current_value: Number,
  threshold_min: Number,
  threshold_max: Number,
  severity: String, // 'low', 'medium', 'high', 'critical'
  message: String,
  status: String, // 'active', 'acknowledged', 'resolved'
  timestamp: Date,
  created_at: Date
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/smarthome_db` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `MQTT_BROKER` | MQTT broker host | `localhost` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `SECRET_KEY` | Flask secret key | `dev-secret-key` |

### MQTT Topics

- `sensor/living_room` - Living room sensor data
- `sensor/bedroom` - Bedroom sensor data  
- `sensor/kitchen` - Kitchen sensor data

## Development

### Project Structure

```
backend/
├── app.py                 # Main Flask application
├── simulate_sensors.py    # Sensor simulation script
├── requirements.txt       # Python dependencies
├── env.example           # Environment configuration template
├── models/
│   ├── __init__.py
│   ├── sensor_data.py    # MongoDB schema and operations
│   └── sensor.py         # Sensor class with buffering
└── services/
    ├── __init__.py
    ├── sensor_service.py  # Sensor data business logic
    └── alert_service.py   # Alert management
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-flask pytest-mock

# Run tests
pytest
```

### Logging

The application uses Python's logging module with configurable levels:
- ERROR: Critical errors and exceptions
- WARNING: Alerts and important events
- INFO: General application flow
- DEBUG: Detailed debugging information

## Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t smart-home-backend .
docker run -p 5001:5001 smart-home-backend
```

### Azure App Service

1. Create Azure App Service
2. Configure environment variables
3. Deploy via Git or Azure CLI

## Monitoring

### Health Check
- `GET /` - Service status and version (http://localhost:5001)

### Metrics
- MongoDB connection status
- Redis connection status  
- MQTT broker connection status
- Active sensor count
- Alert statistics

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Check if MQTT broker is running
   - Verify MQTT_BROKER and MQTT_PORT settings

2. **MongoDB Connection Error**
   - Ensure MongoDB is running and accessible
   - Check MONGO_URI configuration

3. **Redis Connection Error**
   - Verify Redis is running
   - Check REDIS_HOST and REDIS_PORT settings

4. **No Sensor Data**
   - Ensure sensor simulation is running
   - Check MQTT broker logs
   - Verify topic subscription

5. **Port 5000 Already in Use (macOS)**
   - Backend now runs on port 5001 by default
   - This avoids conflicts with AirPlay Receiver on macOS
   - Access the backend at http://localhost:5001

### Logs

Check application logs for detailed error information:
```bash
tail -f app.log
``` 