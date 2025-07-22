from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from models.sensor_data import SensorData

class SensorService:
    """Service class for handling sensor data operations"""
    
    def __init__(self, db, redis_client):
        """
        Initialize sensor service with database and cache connections
        
        Args:
            db: MongoDB database connection
            redis_client: Redis client for caching
        """
        self.db = db
        self.redis_client = redis_client
        self.sensor_data_model = SensorData(db)
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        
        logging.info("SensorService initialized")
    
    def process_sensor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming sensor data, validate, store, and cache
        
        Args:
            data: Raw sensor data from MQTT
            
        Returns:
            dict: Processed sensor data
        """
        try:
            # Validate and normalize data
            validated_data = self.sensor_data_model.validate_data(data)
            
            # Store in MongoDB
            document_id = self.sensor_data_model.insert_reading(validated_data)
            
            # Add document ID to response
            validated_data['_id'] = document_id
            
            # Cache latest reading for quick access
            cache_key = f"sensor:latest:{validated_data['room']}:{validated_data['sensor_type']}"
            self._cache_sensor_data(cache_key, validated_data)
            
            # Update room statistics cache
            self._update_room_stats_cache(validated_data)
            
            logging.info(f"Processed sensor data: {validated_data['sensor_id']} - {validated_data['value']}")
            
            return validated_data
            
        except Exception as e:
            logging.error(f"Error processing sensor data: {e}")
            raise Exception(f"Failed to process sensor data: {e}")
    
    def get_sensor_data(self, room: Optional[str] = None, 
                       sensor_type: Optional[str] = None, 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get sensor data with optional filtering
        
        Args:
            room: Filter by room name
            sensor_type: Filter by sensor type
            limit: Maximum number of records to return
            
        Returns:
            list: Filtered sensor data
        """
        try:
            # Try to get from cache first
            cache_key = f"sensors:{room or 'all'}:{sensor_type or 'all'}:{limit}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                logging.debug(f"Retrieved sensor data from cache: {cache_key}")
                return cached_data
            
            # Get from database
            data = self.sensor_data_model.get_filtered_data(
                room=room,
                sensor_type=sensor_type,
                limit=limit
            )
            
            # Convert ObjectId to string for JSON serialization
            serialized_data = self._serialize_data(data)
            
            # Cache the results
            self._cache_data(cache_key, serialized_data)
            
            return serialized_data
            
        except Exception as e:
            logging.error(f"Error fetching sensor data: {e}")
            return []
    
    def get_latest_by_room(self, room: str, sensor_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get latest sensor readings for a specific room
        
        Args:
            room: Room name
            sensor_types: Optional list of sensor types to filter
            
        Returns:
            dict: Latest sensor readings by type
        """
        try:
            # Check cache first
            cache_key = f"room:latest:{room}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                # Filter by sensor types if specified
                if sensor_types:
                    filtered_data = {k: v for k, v in cached_data.items() if k in sensor_types}
                    return filtered_data
                return cached_data
            
            # Get from database
            data = self.sensor_data_model.get_latest_by_room(room, limit=50)
            
            # Group by sensor type and get latest for each
            latest_by_type = {}
            for reading in data:
                sensor_type = reading['sensor_type']
                if sensor_type not in latest_by_type:
                    latest_by_type[sensor_type] = self._serialize_document(reading)
                elif reading['timestamp'] > datetime.fromisoformat(latest_by_type[sensor_type]['timestamp'].replace('Z', '+00:00')):
                    latest_by_type[sensor_type] = self._serialize_document(reading)
            
            # Cache the results
            self._cache_data(cache_key, latest_by_type)
            
            # Filter by sensor types if specified
            if sensor_types:
                filtered_data = {k: v for k, v in latest_by_type.items() if k in sensor_types}
                return filtered_data
            
            return latest_by_type
            
        except Exception as e:
            logging.error(f"Error fetching latest data for room {room}: {e}")
            return {}
    
    def get_sensor_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated sensor statistics
        
        Returns:
            dict: Sensor statistics
        """
        try:
            # Check cache first
            cache_key = "sensor:statistics"
            cached_stats = self._get_cached_data(cache_key)
            
            if cached_stats:
                return cached_stats
            
            # Get from database
            stats = self.sensor_data_model.get_statistics()
            
            # Add additional computed statistics
            enhanced_stats = self._enhance_statistics(stats)
            
            # Cache the results with shorter TTL (1 minute for stats)
            self._cache_data(cache_key, enhanced_stats, ttl=60)
            
            return enhanced_stats
            
        except Exception as e:
            logging.error(f"Error fetching sensor statistics: {e}")
            return {'error': 'Failed to fetch statistics'}
    
    def _enhance_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add additional computed statistics
        
        Args:
            stats: Base statistics from database
            
        Returns:
            dict: Enhanced statistics
        """
        enhanced = stats.copy()
        
        # Add summary statistics
        if 'by_room_and_type' in stats:
            room_count = len(stats['by_room_and_type'])
            sensor_type_count = set()
            
            for room_data in stats['by_room_and_type'].values():
                sensor_type_count.update(room_data.keys())
            
            enhanced['summary'] = {
                'total_rooms': room_count,
                'total_sensor_types': len(sensor_type_count),
                'sensor_types': list(sensor_type_count)
            }
        
        # Add timestamp
        enhanced['generated_at'] = datetime.utcnow().isoformat()
        
        return enhanced
    
    def _cache_sensor_data(self, key: str, data: Dict[str, Any]):
        """Cache sensor data with error handling"""
        try:
            serialized_data = json.dumps(data, default=str)
            self.redis_client.setex(key, self.cache_ttl, serialized_data)
        except Exception as e:
            logging.warning(f"Failed to cache sensor data: {e}")
    
    def _cache_data(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache any data with error handling"""
        try:
            serialized_data = json.dumps(data, default=str)
            cache_ttl = ttl or self.cache_ttl
            self.redis_client.setex(key, cache_ttl, serialized_data)
        except Exception as e:
            logging.warning(f"Failed to cache data for key {key}: {e}")
    
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache with error handling"""
        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logging.warning(f"Failed to get cached data for key {key}: {e}")
        return None
    
    def _update_room_stats_cache(self, data: Dict[str, Any]):
        """Update room-level statistics cache"""
        try:
            room = data['room']
            sensor_type = data['sensor_type']
            
            # Update latest readings cache
            room_cache_key = f"room:latest:{room}"
            cached_room_data = self._get_cached_data(room_cache_key) or {}
            
            # Update the specific sensor type reading
            cached_room_data[sensor_type] = self._serialize_document(data)
            
            # Cache updated room data
            self._cache_data(room_cache_key, cached_room_data)
            
        except Exception as e:
            logging.warning(f"Failed to update room stats cache: {e}")
    
    def _serialize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize MongoDB documents for JSON response"""
        serialized = []
        for doc in data:
            serialized.append(self._serialize_document(doc))
        return serialized
    
    def _serialize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize a single MongoDB document"""
        serialized = {}
        for key, value in doc.items():
            if key == '_id':
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized
    
    def clear_cache(self, pattern: Optional[str] = None):
        """
        Clear cache entries
        
        Args:
            pattern: Redis key pattern to match (defaults to all sensor cache keys)
        """
        try:
            pattern = pattern or "sensor:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logging.info(f"Cleared {len(keys)} cache entries matching pattern: {pattern}")
        except Exception as e:
            logging.error(f"Failed to clear cache: {e}") 