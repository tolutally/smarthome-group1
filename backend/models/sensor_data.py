from datetime import datetime
from typing import Dict, Any, Optional
import pymongo
from pymongo import MongoClient

class SensorData:
    """MongoDB schema and operations for sensor data"""
    
    # Alert thresholds based on requirements
    THRESHOLDS = {
        'temperature': {'min': 18.0, 'max': 30.0, 'unit': '°C'},
        'humidity': {'min': 30.0, 'max': 70.0, 'unit': '%'},
        'co': {'min': 0.0, 'max': 50.0, 'unit': 'ppm'}
    }
    
    def __init__(self, db):
        """Initialize with MongoDB database connection"""
        self.db = db
        self.collection = db.sensor_data
        self.setup_indexes()
    
    def setup_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Create compound index for efficient queries
            self.collection.create_index([
                ("timestamp", pymongo.DESCENDING),
                ("room", pymongo.ASCENDING),
                ("sensor_type", pymongo.ASCENDING)
            ])
            
            # Create index for sensor_id
            self.collection.create_index("sensor_id")
            
            # Create TTL index to automatically delete old data (optional - keeps 30 days)
            self.collection.create_index("timestamp", expireAfterSeconds=30*24*60*60)
            
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize sensor data"""
        required_fields = ['sensor_id', 'sensor_type', 'value', 'room']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Normalize sensor type
        sensor_type = data['sensor_type'].lower()
        if sensor_type not in self.THRESHOLDS:
            raise ValueError(f"Invalid sensor type: {sensor_type}")
        
        # Validate numeric value
        try:
            value = float(data['value'])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid sensor value: {data['value']}")
        
        # Create normalized document
        normalized_data = {
            'sensor_id': str(data['sensor_id']),
            'sensor_type': sensor_type,
            'value': value,
            'room': str(data['room']).lower(),
            'timestamp': data.get('timestamp', datetime.utcnow()),
            'created_at': datetime.utcnow()
        }
        
        # Add optional fields
        if 'unit' in data:
            normalized_data['unit'] = str(data['unit'])
        else:
            normalized_data['unit'] = self.THRESHOLDS[sensor_type]['unit']
        
        if 'status' in data:
            normalized_data['status'] = str(data['status'])
        else:
            normalized_data['status'] = 'active'
        
        return normalized_data
    
    def insert_reading(self, data: Dict[str, Any]) -> str:
        """Insert a single sensor reading"""
        try:
            validated_data = self.validate_data(data)
            result = self.collection.insert_one(validated_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to insert sensor data: {e}")
    
    def insert_batch(self, data_list: list) -> list:
        """Insert multiple sensor readings"""
        try:
            validated_data = [self.validate_data(data) for data in data_list]
            result = self.collection.insert_many(validated_data)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            raise Exception(f"Failed to insert batch sensor data: {e}")
    
    def get_latest_by_room(self, room: str, limit: int = 10) -> list:
        """Get latest sensor readings for a specific room"""
        try:
            cursor = self.collection.find(
                {'room': room.lower()}
            ).sort('timestamp', -1).limit(limit)
            
            return list(cursor)
        except Exception as e:
            raise Exception(f"Failed to fetch data for room {room}: {e}")
    
    def get_by_sensor_type(self, sensor_type: str, limit: int = 100) -> list:
        """Get latest readings for a specific sensor type"""
        try:
            cursor = self.collection.find(
                {'sensor_type': sensor_type.lower()}
            ).sort('timestamp', -1).limit(limit)
            
            return list(cursor)
        except Exception as e:
            raise Exception(f"Failed to fetch data for sensor type {sensor_type}: {e}")
    
    def get_filtered_data(self, room: Optional[str] = None, 
                         sensor_type: Optional[str] = None, 
                         limit: int = 100) -> list:
        """Get sensor data with optional filtering"""
        try:
            query = {}
            
            if room:
                query['room'] = room.lower()
            
            if sensor_type:
                query['sensor_type'] = sensor_type.lower()
            
            cursor = self.collection.find(query).sort('timestamp', -1).limit(limit)
            return list(cursor)
            
        except Exception as e:
            raise Exception(f"Failed to fetch filtered sensor data: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics for all sensors"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': {
                            'room': '$room',
                            'sensor_type': '$sensor_type'
                        },
                        'count': {'$sum': 1},
                        'avg_value': {'$avg': '$value'},
                        'min_value': {'$min': '$value'},
                        'max_value': {'$max': '$value'},
                        'latest_timestamp': {'$max': '$timestamp'}
                    }
                },
                {
                    '$sort': {'latest_timestamp': -1}
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            # Format results
            stats = {
                'total_readings': self.collection.count_documents({}),
                'by_room_and_type': {}
            }
            
            for result in results:
                room = result['_id']['room']
                sensor_type = result['_id']['sensor_type']
                
                if room not in stats['by_room_and_type']:
                    stats['by_room_and_type'][room] = {}
                
                stats['by_room_and_type'][room][sensor_type] = {
                    'count': result['count'],
                    'average': round(result['avg_value'], 2),
                    'min': result['min_value'],
                    'max': result['max_value'],
                    'latest_timestamp': result['latest_timestamp'],
                    'unit': self.THRESHOLDS[sensor_type]['unit']
                }
            
            return stats
            
        except Exception as e:
            raise Exception(f"Failed to generate statistics: {e}")
    
    def check_threshold_violation(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if sensor reading violates thresholds"""
        sensor_type = data.get('sensor_type', '').lower()
        value = data.get('value')
        
        if sensor_type not in self.THRESHOLDS or value is None:
            return None
        
        thresholds = self.THRESHOLDS[sensor_type]
        
        if value < thresholds['min'] or value > thresholds['max']:
            return {
                'sensor_id': data.get('sensor_id'),
                'room': data.get('room'),
                'sensor_type': sensor_type,
                'value': value,
                'threshold_min': thresholds['min'],
                'threshold_max': thresholds['max'],
                'unit': thresholds['unit'],
                'violation_type': 'below_min' if value < thresholds['min'] else 'above_max',
                'timestamp': data.get('timestamp', datetime.utcnow())
            }
        
        return None 