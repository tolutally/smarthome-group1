import azure.functions as func
import logging
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function for monitoring sensor thresholds
    Triggered by HTTP request or timer
    """
    logging.info('Threshold monitoring function triggered.')
    
    try:
        # Get request data
        req_body = req.get_json()
        
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "No data provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process threshold monitoring
        result = process_threshold_monitoring(req_body)
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in threshold monitoring: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def process_threshold_monitoring(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process sensor data and check thresholds"""
    
    sensor_data = data.get('sensor_data', {})
    threshold_config = data.get('threshold_config', get_default_thresholds())
    notification_config = data.get('notification_config', {})
    
    alerts_triggered = []
    
    # Check each sensor parameter against thresholds
    for parameter, value in sensor_data.items():
        if parameter in threshold_config and value is not None:
            threshold = threshold_config[parameter]
            alert = check_parameter_threshold(
                parameter, value, threshold, sensor_data
            )
            
            if alert:
                alerts_triggered.append(alert)
                
                # Send notification for critical alerts
                if alert['severity'] == 'CRITICAL':
                    send_notification(alert, notification_config)
    
    # Log monitoring results
    logging.info(f"Monitored sensor {sensor_data.get('sensor_id', 'unknown')}: "
                f"{len(alerts_triggered)} alerts triggered")
    
    return {
        "status": "success",
        "sensor_id": sensor_data.get('sensor_id'),
        "alerts_triggered": alerts_triggered,
        "timestamp": datetime.now().isoformat()
    }


def check_parameter_threshold(parameter: str, value: float, 
                             threshold: Dict[str, Any], 
                             sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check if a parameter exceeds its threshold"""
    
    alert = None
    
    if parameter == 'temperature':
        if 'max' in threshold and value > threshold['max']:
            alert = create_alert(
                'HIGH_TEMPERATURE', 
                f"Temperature {value}°C exceeds maximum {threshold['max']}°C",
                'WARNING' if value < threshold['max'] + 5 else 'CRITICAL',
                sensor_data
            )
        elif 'min' in threshold and value < threshold['min']:
            alert = create_alert(
                'LOW_TEMPERATURE',
                f"Temperature {value}°C below minimum {threshold['min']}°C", 
                'WARNING',
                sensor_data
            )
    
    elif parameter == 'humidity':
        if 'max' in threshold and value > threshold['max']:
            alert = create_alert(
                'HIGH_HUMIDITY',
                f"Humidity {value}% exceeds maximum {threshold['max']}%",
                'WARNING',
                sensor_data
            )
        elif 'min' in threshold and value < threshold['min']:
            alert = create_alert(
                'LOW_HUMIDITY',
                f"Humidity {value}% below minimum {threshold['min']}%",
                'WARNING', 
                sensor_data
            )
    
    elif parameter == 'co_level':
        if 'max' in threshold and value > threshold['max']:
            severity = 'CRITICAL' if value > threshold['max'] * 1.5 else 'WARNING'
            alert = create_alert(
                'HIGH_CO_LEVEL',
                f"CO level {value} ppm exceeds safe limit {threshold['max']} ppm",
                severity,
                sensor_data
            )
    
    elif parameter == 'battery_level':
        if 'min' in threshold and value < threshold['min']:
            alert = create_alert(
                'LOW_BATTERY',
                f"Battery level {value}% below minimum {threshold['min']}%",
                'WARNING',
                sensor_data
            )
    
    return alert


def create_alert(alert_type: str, message: str, severity: str, 
                sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized alert object"""
    
    return {
        "id": f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sensor_data.get('sensor_id', 'unknown')}",
        "type": alert_type,
        "sensor_id": sensor_data.get('sensor_id'),
        "room": sensor_data.get('room'),
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "status": "ACTIVE",
        "sensor_data": sensor_data
    }


def send_notification(alert: Dict[str, Any], config: Dict[str, Any]):
    """Send notification for critical alerts"""
    
    try:
        # Send to webhook if configured
        if 'webhook' in config:
            webhook_payload = {
                "alert": alert,
                "notification_type": "threshold_alert",
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                config['webhook'],
                json=webhook_payload,
                timeout=10
            )
            
            logging.info(f"Webhook notification sent: {response.status_code}")
        
        # Send to Smart Home API if configured  
        if 'api_endpoint' in config:
            api_payload = {
                "type": "alert_notification",
                "alert": alert
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config.get('api_token', '')}"
            }
            
            response = requests.post(
                config['api_endpoint'],
                json=api_payload,
                headers=headers,
                timeout=10
            )
            
            logging.info(f"API notification sent: {response.status_code}")
            
    except Exception as e:
        logging.error(f"Failed to send notification: {str(e)}")


def get_default_thresholds() -> Dict[str, Dict[str, float]]:
    """Get default threshold configuration"""
    
    return {
        "temperature": {
            "min": 10.0,   # °C
            "max": 30.0    # °C
        },
        "humidity": {
            "min": 30.0,   # %
            "max": 70.0    # %
        },
        "co_level": {
            "max": 5.0     # ppm (parts per million)
        },
        "battery_level": {
            "min": 20.0    # %
        }
    }


# Timer trigger function (runs every 5 minutes)
def timer_trigger(mytimer: func.TimerRequest) -> None:
    """
    Timer-triggered function for periodic threshold monitoring
    """
    logging.info('Timer trigger threshold monitoring started.')
    
    try:
        # Get recent sensor data from API
        api_endpoint = os.environ.get('SMART_HOME_API_ENDPOINT')
        api_token = os.environ.get('SMART_HOME_API_TOKEN')
        
        if not api_endpoint:
            logging.warning('No API endpoint configured for timer trigger')
            return
        
        headers = {
            'Authorization': f'Bearer {api_token}' if api_token else None
        }
        
        # Fetch recent sensor data
        response = requests.get(
            f"{api_endpoint}/api/sensors/current",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            sensor_data = response.json()
            
            # Process each sensor's data
            for room, data in sensor_data.get('data', {}).items():
                if isinstance(data, dict):
                    monitoring_data = {
                        'sensor_data': data,
                        'threshold_config': get_default_thresholds(),
                        'notification_config': {
                            'webhook': os.environ.get('NOTIFICATION_WEBHOOK'),
                            'api_endpoint': f"{api_endpoint}/api/alerts",
                            'api_token': api_token
                        }
                    }
                    
                    result = process_threshold_monitoring(monitoring_data)
                    logging.info(f"Processed {room}: {len(result.get('alerts_triggered', []))} alerts")
        
    except Exception as e:
        logging.error(f"Timer trigger error: {str(e)}") 