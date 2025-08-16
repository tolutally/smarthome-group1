# 🐳 Docker Setup & Troubleshooting Guide

## 🚨 MongoDB Startup Issue - Solutions

### **Quick Fix: Run Without Docker (Immediate Solution)**
```bash
./start_without_docker.sh
```
**This will:**
- ✅ Start the system immediately without Docker
- ✅ Use in-memory data storage (demo mode)
- ✅ Provide all functionality except data persistence
- ✅ Perfect for testing and demonstrations

---

## 🐳 Docker Desktop Setup (For Full Database Persistence)

### **Step 1: Install Docker Desktop**
1. **Download Docker Desktop**: https://www.docker.com/products/docker-desktop
2. **Install** the application
3. **Start Docker Desktop** from Applications
4. **Wait** for Docker to fully initialize (Docker icon in menu bar should be steady, not animated)

### **Step 2: Verify Docker is Running**
```bash
# Check Docker version
docker --version

# Test Docker daemon
docker info

# Should show Docker system info without errors
```

### **Step 3: Start the Complete System**
```bash
# Use the improved startup script
./start_complete_system_fixed.sh

# Or use the original (after Docker is running)
./start_complete_system.sh
```

---

## 🔧 Troubleshooting Docker Issues

### **Issue 1: "Cannot connect to Docker daemon"**
**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///Users/tobitowoju/.docker/run/docker.sock
```

**Solutions:**
1. **Start Docker Desktop manually**:
   - Open Docker Desktop app from Applications
   - Wait for it to fully start (5-10 seconds)
   - Docker icon in menu bar should be steady

2. **Restart Docker Desktop**:
   - Quit Docker Desktop completely
   - Restart it from Applications
   - Wait for initialization

3. **Check Docker Desktop preferences**:
   - Open Docker Desktop → Settings
   - Ensure "Start Docker Desktop when you log in" is checked

### **Issue 2: "Port already in use"**
**Symptoms:**
```
docker: Error response from daemon: driver failed programming external connectivity on endpoint
```

**Solutions:**
```bash
# Find what's using the port
lsof -i :27017  # For MongoDB
lsof -i :6379   # For Redis
lsof -i :1883   # For MQTT

# Kill the process using the port
kill -9 <PID>

# Or stop all existing containers
docker stop $(docker ps -q)
```

### **Issue 3: "No space left on device"**
**Symptoms:**
```
docker: no space left on device
```

**Solutions:**
```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune -a
```

### **Issue 4: Docker Desktop won't start**
**Solutions:**
1. **Reset Docker Desktop**:
   - Docker Desktop → Troubleshoot → Reset to factory defaults

2. **Restart your Mac**:
   - Sometimes required after Docker installation

3. **Check system requirements**:
   - macOS 10.15 or newer required
   - At least 4GB RAM available

---

## 🚀 Alternative: Quick Demo Mode

### **If Docker Continues to Have Issues:**
```bash
# Start immediately without Docker
./start_without_docker.sh

# Then open the system
open http://localhost:5000
```

**Demo Mode Provides:**
- ✅ Full backend API functionality
- ✅ Real-time WebSocket streaming
- ✅ Interactive frontend dashboard
- ✅ Mock sensor data and alerts
- ✅ Advanced demo UI
- ⚠️  Data doesn't persist (resets on restart)

---

## 📊 Database Alternatives

### **For Development Without Docker:**

1. **MongoDB Atlas (Cloud)**:
   - Free cloud MongoDB instance
   - Update `MONGODB_URI` in `.env`
   - No local installation required

2. **MongoDB Community Edition**:
   - Install directly on macOS
   - ```bash
     brew install mongodb/brew/mongodb-community
     brew services start mongodb/brew/mongodb-community
     ```

3. **Redis Cloud**:
   - Free cloud Redis instance
   - Update `REDIS_URL` in `.env`

---

## 🔍 Verification Commands

### **Check Docker Status:**
```bash
# Docker version
docker --version

# Docker daemon status
docker info

# Running containers
docker ps

# All containers
docker ps -a
```

### **Check System Status:**
```bash
# Run system health check
python3 check_system_status.py

# Check individual components
curl http://localhost:5000/api/userinfo
curl http://localhost:5000/api/sensors
```

---

## 🎯 Recommended Approach

### **For Immediate Demo/Testing:**
1. **Use Docker-free mode**: `./start_without_docker.sh`
2. **Access dashboard**: http://localhost:5000
3. **Start demo UI**: `python3 demo_ui.py`

### **For Full Development:**
1. **Install Docker Desktop properly**
2. **Ensure it starts successfully**
3. **Use full system**: `./start_complete_system_fixed.sh`
4. **Populate with dummy data**: Automatic with the script

---

## 💡 Pro Tips

### **Mac-Specific Docker Tips:**
- **Docker Desktop uses significant resources** - close other heavy apps
- **Check Activity Monitor** for Docker memory usage
- **Restart Docker** if it becomes unresponsive
- **Use Docker Desktop dashboard** to monitor containers

### **For M1/M2 Macs:**
- Ensure you downloaded the **Apple Silicon version** of Docker Desktop
- Some containers may need `--platform linux/amd64` flag
- Performance is generally excellent once properly set up

---

## 🆘 Still Having Issues?

### **Contact Information:**
- **Run**: `python3 check_system_status.py` and share the output
- **Try**: Docker-free mode first: `./start_without_docker.sh`
- **Check**: Docker Desktop logs in the application

### **Fallback Solutions:**
1. **Use demo mode** for immediate functionality
2. **Install MongoDB/Redis directly** via Homebrew
3. **Use cloud database services** (MongoDB Atlas, Redis Cloud)
4. **Focus on frontend development** with mock data

---

**🏠 Remember: The Smart Home system works great in demo mode - you can develop and test all features without Docker!** ✨
