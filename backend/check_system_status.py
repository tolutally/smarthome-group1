#!/usr/bin/env python3
"""
Smart Home System Status Checker
Verifies all components are working correctly
"""
import requests
import subprocess
import json
from pymongo import MongoClient
import redis
from datetime import datetime

def check_mongo():
    """Check MongoDB connection and data"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client.smarthome
        
        # Test connection
        client.admin.command('ismaster')
        
        # Count data
        sensor_count = db.sensor_data.count_documents({})
        alert_count = db.alerts.count_documents({})
        active_alerts = db.alerts.count_documents({"status": "ACTIVE"})
        
        print("✅ MongoDB Status:")
        print(f"   📊 Sensor readings: {sensor_count:,}")
        print(f"   🚨 Total alerts: {alert_count}")
        print(f"   🟢 Active alerts: {active_alerts}")
        
        # Show latest sensor reading
        latest = db.sensor_data.find_one(sort=[("timestamp", -1)])
        if latest:
            print(f"   🕐 Latest reading: {latest['room']} - {latest['temperature']}°C")
        
        return True
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        return False

def check_redis():
    """Check Redis connection"""
    try:
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        info = client.info()
        print("✅ Redis Status:")
        print(f"   📦 Connected clients: {info.get('connected_clients', 0)}")
        print(f"   💾 Used memory: {info.get('used_memory_human', 'Unknown')}")
        return True
    except Exception as e:
        print(f"⚠️  Redis Error: {e}")
        return False

def check_backend():
    """Check backend API"""
    try:
        # Test health endpoint
        response = requests.get('http://localhost:5000/api/userinfo', timeout=5)
        if response.status_code == 200:
            print("✅ Backend API Status:")
            print("   🌐 Main API: Running on port 5000")
            
            # Test sensor endpoint
            sensor_response = requests.get('http://localhost:5000/api/sensors', timeout=5)
            if sensor_response.status_code == 200:
                print("   📊 Sensor API: Working")
            else:
                print("   ⚠️  Sensor API: Issues detected")
            
            return True
        else:
            print(f"❌ Backend API Error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend API Error: {e}")
        return False

def check_demo_ui():
    """Check demo UI"""
    try:
        response = requests.get('http://localhost:5001/api/demo/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Demo UI Status:")
            print(f"   🎛️  Demo UI: Running on port 5001")
            print(f"   🎮 Simulation: {'Active' if data.get('simulation_active') else 'Stopped'}")
            return True
        else:
            print("⚠️  Demo UI: Not running (optional)")
            return False
    except Exception as e:
        print("⚠️  Demo UI: Not running (optional)")
        return False

def check_docker_containers():
    """Check Docker containers"""
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                               capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        if 'smart-home' in container.get('Names', ''):
                            containers.append(container)
                    except:
                        pass
            
            print("🐳 Docker Containers:")
            for container in containers:
                name = container.get('Names', 'Unknown')
                status = container.get('Status', 'Unknown')
                ports = container.get('Ports', 'No ports')
                print(f"   📦 {name}: {status}")
                if ports != 'No ports':
                    print(f"      Ports: {ports}")
            
            return len(containers) > 0
        else:
            print("❌ Docker Error: Could not list containers")
            return False
    except Exception as e:
        print(f"❌ Docker Error: {e}")
        return False

def check_ports():
    """Check if required ports are available"""
    import socket
    
    ports = {
        5000: "Backend API",
        5001: "Demo UI", 
        27017: "MongoDB",
        6379: "Redis",
        1883: "MQTT"
    }
    
    print("🔌 Port Status:")
    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                print(f"   ✅ Port {port}: {service} - Active")
            else:
                print(f"   ❌ Port {port}: {service} - Not accessible")
        except:
            print(f"   ❌ Port {port}: {service} - Error")
        finally:
            sock.close()

def main():
    """Run all status checks"""
    print("🏠 Smart Home System Status Check")
    print("=" * 50)
    print(f"🕐 Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    checks = [
        check_ports,
        check_docker_containers,
        check_mongo,
        check_redis,
        check_backend,
        check_demo_ui
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            result = check()
            if result:
                passed += 1
            print("")
        except Exception as e:
            print(f"❌ Check failed: {e}")
            print("")
    
    print("📋 Summary:")
    print(f"   Passed: {passed}/{total} checks")
    
    if passed == total:
        print("🎉 All systems operational!")
    elif passed >= total - 2:
        print("✅ System mostly operational")
    else:
        print("⚠️  System has issues that need attention")
    
    print("")
    print("💡 Quick Actions:")
    print("   Start system:     ./start_complete_system.sh")
    print("   Seed database:    python3 seed_database.py")
    print("   Start demo UI:    python3 demo_ui.py")
    print("   View frontend:    open http://localhost:5000")

if __name__ == "__main__":
    main()
