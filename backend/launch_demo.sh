#!/bin/bash

echo "🏠 Smart Home Backend Demo UI Launcher"
echo "======================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "demo_ui.py" ]; then
    echo "❌ Error: demo_ui.py not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Check if Flask-SocketIO is installed
python3 -c "import flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Flask-SocketIO not found. Installing required dependencies..."
    pip3 install flask flask-socketio flask-cors
fi

echo "🚀 Starting Smart Home Backend Demo UI..."
echo ""
echo "📊 Dashboard will be available at: http://localhost:5005"
echo "🔌 WebSocket server will run on port 5005"
echo ""
echo "🎯 Demo Features:"
echo "   • Real-time sensor monitoring"
echo "   • Live alert management"
echo "   • WebSocket communication"
echo "   • Azure Function simulation"
echo "   • Multi-channel notifications"
echo "   • Interactive testing controls"
echo ""
echo "⏹️  Press Ctrl+C to stop the demo"
echo ""

# Launch the demo UI
python3 demo_ui.py 