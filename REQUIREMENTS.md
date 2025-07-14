# Smart Home System - Technical Requirements Document

## Overview
This document outlines the technical specifications and requirements for the CST8922 Smart Home System Prototype. The system consists of real-time sensor simulation, backend API with alerts and authentication, and an interactive dashboard frontend.

---

## 🔧 BACKEND - TECHNICAL SPECIFICATIONS

| Component | Technology / Tool | Purpose |
|-----------|------------------|---------|
| **Server Framework** | Python + Flask | Build REST API and backend logic |
| **API Type** | Flask-SocketIO | Enable WebSocket for real-time updates |
| **Authentication** | Microsoft OAuth2/Azure Active Directory | Secure user login and session control |
| **Alert Trigger** | Azure Functions (Python) | Send alerts when thresholds are crossed |
| **Error Handling** | Python try/except + logging | Catch runtime errors and maintain logs |
| **Testing** | Postman, Pytest | Validate API endpoints and alert behavior |
| **Deployment** | Azure App Service | Host backend server in cloud |

---

## 💻 FRONTEND - TECHNICAL SPECIFICATIONS

| Component | Technology / Tool | Purpose |
|-----------|------------------|---------|
| **Languages** | HTML, CSS, JavaScript | Build interactive user dashboard |
| **Charts/Graphs** | Chart.js | Visualize sensor data per room |
| **Real-Time Feed** | Socket.io Client (JavaScript) | Receive live updates from backend |
| **Authentication UI** | Microsoft OAuth2 | Integrate login on dashboard |
| **Styling** | Tailwind CSS or Bootstrap | Create responsive and clean UI |
| **Testing** | Browser DevTools | Inspect, debug, and test UI components |

---

## ☁️ DATA / INTEGRATION - AZURE HOSTING PLAN

| Component | Technology / Tool | Azure Hosting | Purpose |
|-----------|------------------|---------------|---------|
| **Sensor Protocol** | MQTT (paho-mqtt in Python) | Azure IoT Hub (optional) or Local MQTT Broker | IoT Hub adds complexity; local Mosquitto is faster to test |
| **Sensor Simulation** | Python Script | Local or Azure VM / Container Instance | Lightweight script to run on dev or VM |
| **Hub Logic** | Python + Buffer Logic | Azure Container App or VM | Can be packaged as container and scale later |
| **Broker** | Eclipse Mosquitto | Azure VM or IoT Edge Module | No native Mosquitto in Azure, so VM is easiest |
| **Database** | MongoDB | Azure Cosmos DB (Mongo API) | Fully managed NoSQL with MongoDB compatibility |
| **Caching** | Redis | Azure Cache for Redis | Fully managed in-memory caching layer |

### 📋 Deployment Strategy
- **Quick Prototyping**: Run MQTT + Python scripts locally
- **Database**: Use Azure Cosmos DB (Mongo API) to avoid managing a database server
- **Caching**: Use Azure Cache for Redis directly (plug-and-play)
- **Future Scaling**: Consider migrating to Azure IoT Hub if MQTT broker grows

---

## 🔐 AUTHENTICATION WITH MICROSOFT (MSAL)

### Implementation Steps:
1. **Register app in Azure Entra ID**
2. **Set up MSAL.js in frontend** for sign-in
3. **Configure backend** to validate JWT access tokens
4. **Restrict certain routes** unless user is authenticated

---

## 📡 SENSOR SIMULATION SETUP

### Requirements:
- **Data Frequency**: Simulate data every 5 seconds per room
- **Data Format**: JSON structure: `{sensorID, type, value, timestamp}`
- **MQTT Publishing**: Publish to topic `sensor/room_name`
- **Offline Buffer**: Implement buffer if no network connection

### Example Data Structure:
```json
{
  "sensorID": "sensor_001",
  "type": "temperature",
  "value": 22.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## ⚡ REAL-TIME INTEGRATION

### Architecture:
1. **MQTT Broker**: Eclipse Mosquitto running locally/cloud
2. **Backend Integration**: Flask subscribes to broker and pushes data to MongoDB
3. **WebSocket Communication**: Flask emits data to frontend using WebSocket
4. **Frontend Updates**: Frontend listens and updates charts in real-time

### Data Flow:
```
Sensor Simulation → MQTT Broker → Flask Backend → MongoDB + WebSocket → Frontend Dashboard
```

---

## 🚨 ALERT SYSTEM

### Alert Logic:
- **Threshold Processing**: Implemented inside Flask or Azure Function
- **Trigger Conditions**: Alert triggered when temperature/humidity/CO goes out of bounds
- **User Notification**: Alert shown on frontend dashboard
- **Data Persistence**: Log all alerts in MongoDB

### Alert Thresholds:
| Sensor Type | Min Value | Max Value | Unit |
|-------------|-----------|-----------|------|
| Temperature | 18°C | 30°C | Celsius |
| Humidity | 30% | 70% | Percentage |
| CO Level | 0 ppm | 50 ppm | Parts per million |

---

## 🛠️ DEVELOPMENT WORKFLOW

### Testing Strategy:
- **Backend**: Use Postman for API testing, Pytest for unit tests
- **Frontend**: Browser DevTools for debugging and testing
- **Integration**: End-to-end testing with real sensor data simulation

### Deployment Pipeline:
1. **Local Development**: Test with local MQTT broker and MongoDB
2. **Staging**: Deploy to Azure services for integration testing
3. **Production**: Full Azure deployment with monitoring and logging

---

## 📋 TECHNICAL DEPENDENCIES

### Python Packages:
- Flask, Flask-SocketIO
- paho-mqtt
- pymongo
- redis
- azure-functions
- pytest

### Frontend Libraries:
- Chart.js
- Socket.io Client
- MSAL.js
- Tailwind CSS / Bootstrap

### Azure Services:
- Azure App Service
- Azure Cosmos DB
- Azure Cache for Redis
- Azure Functions
- Azure Entra ID 