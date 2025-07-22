from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from models.sensor_data import SensorData

class AlertService:
    """Service class for handling alerts and threshold monitoring"""
    
    def __init__(self, db, socketio):
        """
        Initialize alert service
        
        Args:
            db: MongoDB database connection
            socketio: SocketIO instance for real-time notifications
        """
        self.db = db
        self.socketio = socketio
        self.alerts_collection = db.alerts
        
        # Alert configuration
        self.thresholds = SensorData.THRESHOLDS
        self.alert_cooldown = 300  # 5 minutes cooldown between same alerts
        
        # Setup alerts collection indexes
        self._setup_alerts_indexes()
        
        logging.info("AlertService initialized")
    
    def _setup_alerts_indexes(self):
        """Create indexes for alerts collection"""
        try:
            # Create compound index for efficient queries
            self.alerts_collection.create_index([
                ("timestamp", -1),
                ("status", 1),
                ("room", 1)
            ])
            
            # Create index for sensor_id
            self.alerts_collection.create_index("sensor_id")
            
            # Create index for alert_type
            self.alerts_collection.create_index("alert_type")
            
        except Exception as e:
            logging.warning(f"Error creating alert indexes: {e}")
    
    def check_thresholds(self, sensor_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if sensor reading violates thresholds and create alert if needed
        
        Args:
            sensor_data: Validated sensor data
            
        Returns:
            dict: Alert information if threshold violated, None otherwise
        """
        try:
            # Check for threshold violation
            violation = SensorData({}).check_threshold_violation(sensor_data)
            
            if not violation:
                return None
            
            # Check if we should create a new alert (cooldown logic)
            if self._is_in_cooldown(violation):
                logging.debug(f"Alert in cooldown for sensor {violation['sensor_id']}")
                return None
            
            # Create alert document
            alert = self._create_alert(violation, sensor_data)
            
            # Store alert in database
            alert_id = self.alerts_collection.insert_one(alert).inserted_id
            alert['_id'] = str(alert_id)
            
            # Emit real-time alert notification
            self._emit_alert_notification(alert)
            
            logging.warning(f"ALERT: {alert['alert_type']} for {alert['sensor_id']} in {alert['room']} - Value: {alert['current_value']}")
            
            return alert
            
        except Exception as e:
            logging.error(f"Error checking thresholds: {e}")
            return None
    
    def _create_alert(self, violation: Dict[str, Any], sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create alert document from threshold violation
        
        Args:
            violation: Threshold violation information
            sensor_data: Original sensor data
            
        Returns:
            dict: Alert document
        """
        alert_type = f"{violation['sensor_type']}_{violation['violation_type']}"
        
        alert = {
            'alert_id': f"alert_{violation['sensor_id']}_{int(datetime.utcnow().timestamp())}",
            'sensor_id': violation['sensor_id'],
            'room': violation['room'],
            'sensor_type': violation['sensor_type'],
            'alert_type': alert_type,
            'current_value': violation['value'],
            'threshold_min': violation['threshold_min'],
            'threshold_max': violation['threshold_max'],
            'unit': violation['unit'],
            'violation_type': violation['violation_type'],
            'severity': self._calculate_severity(violation),
            'message': self._generate_alert_message(violation),
            'status': 'active',
            'timestamp': violation['timestamp'],
            'created_at': datetime.utcnow(),
            'acknowledged': False,
            'acknowledged_by': None,
            'acknowledged_at': None,
            'resolved': False,
            'resolved_at': None
        }
        
        return alert
    
    def _calculate_severity(self, violation: Dict[str, Any]) -> str:
        """
        Calculate alert severity based on how far the value is from thresholds
        
        Args:
            violation: Threshold violation information
            
        Returns:
            str: Severity level (low, medium, high, critical)
        """
        value = violation['value']
        min_threshold = violation['threshold_min']
        max_threshold = violation['threshold_max']
        
        if violation['violation_type'] == 'below_min':
            deviation_percent = abs((value - min_threshold) / min_threshold * 100)
        else:  # above_max
            deviation_percent = abs((value - max_threshold) / max_threshold * 100)
        
        # Special handling for CO sensor (more critical)
        if violation['sensor_type'] == 'co':
            if deviation_percent > 50:
                return 'critical'
            elif deviation_percent > 20:
                return 'high'
            elif deviation_percent > 10:
                return 'medium'
            else:
                return 'low'
        
        # Regular sensors (temperature, humidity)
        if deviation_percent > 100:
            return 'critical'
        elif deviation_percent > 50:
            return 'high'
        elif deviation_percent > 25:
            return 'medium'
        else:
            return 'low'
    
    def _generate_alert_message(self, violation: Dict[str, Any]) -> str:
        """
        Generate human-readable alert message
        
        Args:
            violation: Threshold violation information
            
        Returns:
            str: Alert message
        """
        sensor_type = violation['sensor_type'].title()
        room = violation['room'].title()
        value = violation['value']
        unit = violation['unit']
        
        if violation['violation_type'] == 'below_min':
            threshold = violation['threshold_min']
            direction = "below"
        else:
            threshold = violation['threshold_max']
            direction = "above"
        
        return f"{sensor_type} in {room} is {direction} safe levels: {value}{unit} (threshold: {threshold}{unit})"
    
    def _is_in_cooldown(self, violation: Dict[str, Any]) -> bool:
        """
        Check if similar alert is in cooldown period
        
        Args:
            violation: Threshold violation information
            
        Returns:
            bool: True if in cooldown, False otherwise
        """
        try:
            cooldown_time = datetime.utcnow() - timedelta(seconds=self.alert_cooldown)
            
            # Check for recent similar alerts
            recent_alert = self.alerts_collection.find_one({
                'sensor_id': violation['sensor_id'],
                'sensor_type': violation['sensor_type'],
                'violation_type': violation['violation_type'],
                'timestamp': {'$gte': cooldown_time},
                'status': 'active'
            })
            
            return recent_alert is not None
            
        except Exception as e:
            logging.error(f"Error checking alert cooldown: {e}")
            return False
    
    def _emit_alert_notification(self, alert: Dict[str, Any]):
        """
        Emit real-time alert notification via WebSocket
        
        Args:
            alert: Alert document
        """
        try:
            # Prepare notification payload
            notification = {
                'type': 'alert',
                'alert': {
                    'id': alert['alert_id'],
                    'message': alert['message'],
                    'severity': alert['severity'],
                    'room': alert['room'],
                    'sensor_type': alert['sensor_type'],
                    'current_value': alert['current_value'],
                    'unit': alert['unit'],
                    'timestamp': alert['timestamp'].isoformat() if isinstance(alert['timestamp'], datetime) else alert['timestamp']
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Emit to all connected clients
            self.socketio.emit('new_alert', notification)
            
            # Emit to room-specific channel if needed
            self.socketio.emit(f'room_alert_{alert["room"]}', notification)
            
            logging.info(f"Emitted alert notification: {alert['alert_id']}")
            
        except Exception as e:
            logging.error(f"Error emitting alert notification: {e}")
    
    def get_alerts(self, limit: int = 50, status: Optional[str] = None,
                   room: Optional[str] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering
        
        Args:
            limit: Maximum number of alerts to return
            status: Filter by alert status
            room: Filter by room
            severity: Filter by severity level
            
        Returns:
            list: Filtered alerts
        """
        try:
            query = {}
            
            if status:
                query['status'] = status
            if room:
                query['room'] = room.lower()
            if severity:
                query['severity'] = severity.lower()
            
            cursor = self.alerts_collection.find(query).sort('timestamp', -1).limit(limit)
            alerts = list(cursor)
            
            # Serialize for JSON response
            serialized_alerts = []
            for alert in alerts:
                serialized_alert = self._serialize_alert(alert)
                serialized_alerts.append(serialized_alert)
            
            return serialized_alerts
            
        except Exception as e:
            logging.error(f"Error fetching alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.alerts_collection.update_one(
                {'alert_id': alert_id},
                {
                    '$set': {
                        'acknowledged': True,
                        'acknowledged_by': acknowledged_by,
                        'acknowledged_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logging.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                
                # Emit acknowledgment notification
                self.socketio.emit('alert_acknowledged', {
                    'alert_id': alert_id,
                    'acknowledged_by': acknowledged_by,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.alerts_collection.update_one(
                {'alert_id': alert_id},
                {
                    '$set': {
                        'resolved': True,
                        'resolved_at': datetime.utcnow(),
                        'status': 'resolved'
                    }
                }
            )
            
            if result.modified_count > 0:
                logging.info(f"Alert {alert_id} resolved")
                
                # Emit resolution notification
                self.socketio.emit('alert_resolved', {
                    'alert_id': alert_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error resolving alert {alert_id}: {e}")
            return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics
        
        Returns:
            dict: Alert statistics
        """
        try:
            # Count alerts by status
            status_stats = list(self.alerts_collection.aggregate([
                {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
            ]))
            
            # Count alerts by severity
            severity_stats = list(self.alerts_collection.aggregate([
                {'$group': {'_id': '$severity', 'count': {'$sum': 1}}}
            ]))
            
            # Count alerts by room
            room_stats = list(self.alerts_collection.aggregate([
                {'$group': {'_id': '$room', 'count': {'$sum': 1}}}
            ]))
            
            # Recent alerts (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_count = self.alerts_collection.count_documents({
                'timestamp': {'$gte': yesterday}
            })
            
            return {
                'total_alerts': self.alerts_collection.count_documents({}),
                'recent_alerts_24h': recent_count,
                'by_status': {stat['_id']: stat['count'] for stat in status_stats},
                'by_severity': {stat['_id']: stat['count'] for stat in severity_stats},
                'by_room': {stat['_id']: stat['count'] for stat in room_stats},
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error generating alert statistics: {e}")
            return {'error': 'Failed to generate statistics'}
    
    def _serialize_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize alert document for JSON response
        
        Args:
            alert: Alert document from MongoDB
            
        Returns:
            dict: Serialized alert
        """
        serialized = {}
        for key, value in alert.items():
            if key == '_id':
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized 