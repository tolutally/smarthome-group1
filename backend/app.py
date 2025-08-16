from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import paho.mqtt.client as mqtt
from pymongo import MongoClient
import redis
import json
import logging
from datetime import datetime
import os
import secrets
import random
import threading
import time
from dotenv import load_dotenv
from models.sensor_data import SensorData
from services.sensor_service import SensorService
from services.alert_service import AlertService
from authlib.integrations.flask_client import OAuth

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Generate server passkey
PASSKEY = secrets.token_hex(16)  # 32-character hex string
print(f"🔑 Server Passkey: {PASSKEY}")

# Global variables for streaming control
streaming_active = False
connected_clients = set()

def send_mock_sensor_data():
    """Send mock sensor data in the format expected by frontend"""
    # Generate realistic mock data for each room
    mock_data = {
        "Living Room": {
            "temperature": round(random.uniform(20, 26), 1),
            "humidity": round(random.uniform(40, 60), 1),
            "co_level": round(random.uniform(0.5, 2.5), 1),
            "timestamp": datetime.now().isoformat() + "Z"
        },
        "Kitchen": {
            "temperature": round(random.uniform(22, 28), 1),
            "humidity": round(random.uniform(45, 65), 1),
            "co_level": round(random.uniform(0.8, 3.2), 1),
            "timestamp": datetime.now().isoformat() + "Z"
        },
        "Garage": {
            "temperature": round(random.uniform(15, 25), 1),
            "humidity": round(random.uniform(35, 55), 1),
            "co_level": round(random.uniform(1.0, 4.0), 1),
            "timestamp": datetime.now().isoformat() + "Z"
        },
        "Basement": {
            "temperature": round(random.uniform(18, 22), 1),
            "humidity": round(random.uniform(50, 70), 1),
            "co_level": round(random.uniform(0.3, 2.0), 1),
            "timestamp": datetime.now().isoformat() + "Z"
        }
    }
    
    # Emit the data using the event name the frontend expects
    socketio.emit('temperature_data', mock_data)
    print(f"Sent mock sensor data: {mock_data}")

def send_periodic_data():
    """Continuously send sensor data while streaming is active"""
    while streaming_active:
        time.sleep(5)
        if streaming_active:
            send_mock_sensor_data()

def start_periodic_data_sending():
    """Start periodic sensor data updates"""
    threading.Thread(target=send_periodic_data, daemon=True).start()
    print("Started periodic sensor data updates (every 5 seconds)")

CORS(app)

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', '390952176863-3h63tpc9t7ot83srjdiagnhl2obtgef4.apps.googleusercontent.com'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', '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'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'
    },
)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize MongoDB
mongo_client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = mongo_client.smarthome_db

# Initialize Redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Initialize services - Commented out for now
# sensor_service = SensorService(db, redis_client)
# alert_service = AlertService(db, socketio)

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
    """Serve the frontend HTML file"""
    try:
        return send_from_directory('../frontend', 'index.html')
    except Exception as e:
        return jsonify({
            'message': 'Smart Home Backend API',
            'version': '1.0.0',
            'status': 'running',
            'error': f'Could not serve frontend: {str(e)}'
        })

@app.route('/api/userinfo')
def userinfo():
    """Get current user information"""
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify({})

@app.route('/auth/google')
def google_auth():
    """Initiate Google OAuth authentication with account selection"""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(
        redirect_uri,
        prompt='select_account'
    )

@app.route('/auth/callback')
def google_callback():
    """Handle Google OAuth callback"""
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        session['user'] = {
            'name': user_info.get('name'),
            'email': user_info.get('email'),
            'picture': user_info.get('picture')
        }
        return redirect('/')
    else:
        return redirect('/?error=auth_failed')

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user', None)
    return redirect('/')

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """Get all sensor data with optional filtering"""
    try:
        room = request.args.get('room')
        sensor_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))
        
        # Mock sensor data instead of sensor_service
        sensors = [
            {
                "id": "temp_001",
                "type": "temperature",
                "location": "Living Room",
                "value": 22.5,
                "unit": "°C",
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "active"
            },
            {
                "id": "hum_001", 
                "type": "humidity",
                "location": "Living Room",
                "value": 45.0,
                "unit": "%",
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "active"
            }
        ]

        # Commented out for now
        # sensors = sensor_service.get_sensor_data(
        #     room=room, 
        #     sensor_type=sensor_type, 
        #     limit=limit
        # )
        
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
        
        # Mock alerts data instead of alert_service
        alerts = [
            {
                "id": "alert_001",
                "sensor_id": "temp_001",
                "type": "temperature",
                "message": "Temperature is high in Living Room",
                "severity": "warning",
                "value": 28.5,
                "threshold": 25.0,
                "timestamp": "2024-01-15T10:25:00Z",
                "status": "active",
                "location": "Living Room"
            }
        ]

        # Commented out for now
        # alerts = alert_service.get_alerts(limit=limit, status=status)
        
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
        # Mock sensor statistics instead of sensor_service
        stats = {
            "total_sensors": 4,
            "active_sensors": 4,
            "inactive_sensors": 0,
            "rooms": ["Living Room", "Kitchen", "Bedroom", "Bathroom"],
            "sensor_types": ["temperature", "humidity", "motion", "light"],
            "avg_temperature": 23.2,
            "avg_humidity": 48.5,
            "last_update": "2024-01-15T10:30:00Z"
        }

        # Commented out for now
        # stats = sensor_service.get_sensor_statistics()
        
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

@app.route('/get-passkey', methods=['GET'])
def get_passkey():
    """Get the server passkey for authentication"""
    return jsonify({"passkey": PASSKEY})

@app.route('/api/network/status', methods=['GET'])
def get_network_status_reference():
    """Get MQTT network status"""
    return jsonify({
        "mqtt_connected": True,  # Mock as True for demonstration
        "redis_connected": False,  # No Redis in current backend
        "cached_items": 0  # No caching in current backend
    })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'message': 'Connected to Smart Home Backend'})

@socketio.on('authenticate')
def handle_authenticate(data):
    """Handle client authentication with passkey"""
    print(f"Received authentication request: {data}")
    provided_passkey = data.get('passkey', '')
    print(f"Provided passkey: '{provided_passkey}', Expected: '{PASSKEY}'")

    if provided_passkey == PASSKEY:
        connected_clients.add(request.sid)
        global streaming_active
        if not streaming_active:
            streaming_active = True
            start_periodic_data_sending()
        
        emit('auth_success', {'message': 'Authentication successful'})
        # Send initial data immediately after authentication
        send_mock_sensor_data()
        print(f'Client {request.sid} authenticated successfully')
    else:
        emit('auth_error', {'message': 'Invalid passkey'})
        print(f'Client {request.sid} authentication failed')

@socketio.on('stop_stream')
def handle_stop_stream():
    """Handle explicit stop stream request"""
    if request.sid in connected_clients:
        connected_clients.remove(request.sid)
    
    # Stop streaming if no clients connected
    if not connected_clients:
        global streaming_active
        streaming_active = False
        print('Stream stopped by user request')
    else:
        print(f'Client {request.sid} stopped receiving stream, {len(connected_clients)} clients remaining')
    
    print('Client disconnected')

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get port from environment variable or use default (5001 to avoid macOS AirPlay on 5000)
    port = int(os.getenv('FLASK_PORT', 5001))
    
    # Connect to MQTT broker - Commented out for now
    # try:
    #     mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    #     mqtt_client.loop_start()
    # except Exception as e:
    #     logging.error(f"Failed to connect to MQTT broker: {e}")
    
    # Run the Flask app with SocketIO
    print(f"🚀 Starting Smart Home Backend on http://localhost:{port}")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use!")
            print(f"💡 Trying alternative port {port + 1}...")
            socketio.run(app, debug=True, host='0.0.0.0', port=port + 1, allow_unsafe_werkzeug=True)
        else:
            raise 