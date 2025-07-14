# CST8922 Smart Home System Prototype

This project is a collaborative smart home monitoring system built by Group 1. It consists of:

- Real-time sensor simulation
- Backend API with alerts and authentication
- Interactive dashboard frontend

---

## 📁 Project Structure

| Folder              | Description |
|---------------------|-------------|
| `/frontend/`        | HTML, JS, OAuth2, Tailwind/Bootstrap |
| `/backend/`         | Flask API, WebSocket, Azure Functions |
| `/data-integration/`| Sensor simulation, MQTT, MongoDB, Redis |
| `/test/`            | Unit test files, well labeled |

---

## 👥 Contributor Guidelines

### 1. Clone the shared repository:
```bash
git clone https://github.com/<your-group-org>/smart-home-prototype.git
```

### 2. Work in your assigned folder only:

| Member | Folder | Responsibility |
|--------|--------|----------------|
| Tobi | `/backend/` | Flask API, Azure Functions, OAuth |
| Ridley | `/data-integration/` | MQTT broker, sensor logic, database |
| Tong | `/frontend/` | UI layout, charts, WebSocket, login form |

**Each person pushes only to their assigned directory.**

### 3. Branching & Commits
Use a feature branch:

```bash
git checkout -b backend/api-endpoints
git checkout -b frontend/login-ui
git checkout -b data/sensor-mqtt
```

Push changes:

```bash
git add .
git commit -m "Add Flask route for storing sensor data"
git push origin <your-branch-name>
```

Open a pull request to main when your part is complete and tested.

### 4. Environment Variables
Copy `.env.example` to `.env` and fill in required values:

```bash
cp .env.example .env
```

Example variables:

```makefile
MONGO_URI=
REDIS_HOST=
MQTT_BROKER=
AZURE_FUNCTION_KEY=
OAUTH_CLIENT_ID=
```

### 5. How to Run (Locally)
Each module runs independently:

**Backend**
```bash
cd backend/
pip install -r ../requirements.txt
flask run
```

**Frontend**
Open `frontend/index.html` in your browser.

**Data Integration**
```bash
cd data-integration/
python simulate_sensors.py
```

### 6. Testing
All test files go in `/test/`.

```bash
cd test/
pytest
```

### 7. Weekly Merge Protocol
- Each member commits to main only through Pull Requests
- Use clear commit messages
- Review each other's code before merging

---

## 🔐 Notes
- No sensitive tokens or credentials in code. Use `.env`.
- Respect folder boundaries to avoid code conflicts. 