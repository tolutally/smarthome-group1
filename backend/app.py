from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import paho.mqtt.client as mqtt
from pymongo import MongoClient
import redis
import json
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
from models.sensor_data import SensorData
from services.sensor_service import SensorService
from services.alert_service import AlertService

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize MongoDB
mongo_client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = mongo_client.smarthome_db

# Initialize Redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Initialize services
sensor_service = SensorService(db, redis_client)
alert_service = AlertService(db, socketio)

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = "sensor/+"

# MQTT Client
mqtt_client = mqtt.Client()

def on_mqtt_connect(client, userdata, flags, rc):
    """Callback for when MQTT client connects"""
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logging.info("MQTT client connected and subscribed to sensor topics")
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")
        logging.error(f"MQTT connection failed with code {rc}")

def on_mqtt_message(client, userdata, msg):
    """Callback for when MQTT message is received"""
    try:
        # Decode the message
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        
        print(f"Received MQTT message on topic {topic}: {payload}")
        
        # Process sensor data
        sensor_data = sensor_service.process_sensor_data(payload)
        
        # Check for alerts
        alert = alert_service.check_thresholds(sensor_data)
        
        # Emit real-time data to connected clients
        socketio.emit('sensor_data', {
            'data': sensor_data,
            'alert': alert
        })
        
        logging.info(f"Processed sensor data: {sensor_data}")
        
    except Exception as e:
        logging.error(f"Error processing MQTT message: {e}")

# Configure MQTT callbacks
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

# API Routes
@app.route('/')
def index():
    return jsonify({
        'message': 'Smart Home Backend API',
        'version': '1.0.0',
        'status': 'running'
    })

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """Get all sensor data with optional filtering"""
    try:
        room = request.args.get('room')
        sensor_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))
        
        sensors = sensor_service.get_sensor_data(
            room=room, 
            sensor_type=sensor_type, 
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': sensors,
            'count': len(sensors)
        })
        
    except Exception as e:
        logging.error(f"Error fetching sensor data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts with optional filtering"""
    try:
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status')
        
        alerts = alert_service.get_alerts(limit=limit, status=status)
        
        return jsonify({
            'success': True,
            'data': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        logging.error(f"Error fetching alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sensor-stats', methods=['GET'])
def get_sensor_stats():
    """Get aggregated sensor statistics"""
    try:
        stats = sensor_service.get_sensor_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logging.error(f"Error fetching sensor stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'message': 'Connected to Smart Home Backend'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get port from environment variable or use default
    port = int(os.getenv('FLASK_PORT', 5001))
    
    # Connect to MQTT broker
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
    
    # Run the Flask app with SocketIO - Changed port to 5001 to avoid macOS AirPlay conflict
    print(f"🚀 Starting Smart Home Backend on http://localhost:{port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port) 