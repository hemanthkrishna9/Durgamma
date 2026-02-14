#!/usr/bin/env bash
# ============================================================
# Mission Control — Server Setup Script
# Run this ON the Azure VM (via deploy.sh or manually)
# ============================================================
set -euo pipefail

echo "=========================================="
echo "  Mission Control — Server Setup"
echo "=========================================="

# --- System packages ---
echo "[1/7] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nodejs npm nginx git curl > /dev/null 2>&1
echo "  Done."

# --- Clone or update repo ---
echo "[2/7] Setting up application code..."
APP_DIR="$HOME/Durgamma"
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git fetch origin
    git checkout claude/ai-agent-squad-platform-MtgpA
    git pull origin claude/ai-agent-squad-platform-MtgpA
    echo "  Repo updated."
else
    git clone -b claude/ai-agent-squad-platform-MtgpA https://github.com/hemanthkrishna9/Durgamma.git "$APP_DIR"
    cd "$APP_DIR"
    echo "  Repo cloned."
fi

# --- Backend setup ---
echo "[3/7] Setting up backend..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate
echo "  Backend dependencies installed."

# --- Frontend setup ---
echo "[4/7] Building frontend..."
cd "$APP_DIR/frontend"
npm install --silent 2>/dev/null
npm run build
echo "  Frontend built."

# --- Environment file ---
echo "[5/7] Configuring environment..."
cat > "$APP_DIR/.env" << 'ENVEOF'
MC_APP_NAME=Mission Control
MC_DATABASE_URL=sqlite+aiosqlite:///./mission_control.db
MC_CORS_ORIGINS=["http://localhost","http://localhost:3000","http://20.119.62.230","http://20.119.62.230:3000","http://20.119.62.230:8000"]
MC_MISSIONS_DIR=/home/azureuser/Durgamma/missions
MC_AGENT_TEMPLATES_DIR=/home/azureuser/Durgamma/agent-templates
ENVEOF

# Append API key if provided
if [ -n "${MC_ANTHROPIC_API_KEY:-}" ]; then
    echo "MC_ANTHROPIC_API_KEY=$MC_ANTHROPIC_API_KEY" >> "$APP_DIR/.env"
    echo "  Anthropic API key configured."
fi
echo "  Environment configured."

# --- Create directories ---
mkdir -p "$APP_DIR/missions"
mkdir -p "$APP_DIR/backend/data"

# --- Systemd services ---
echo "[6/7] Setting up systemd services..."

# Backend service
sudo tee /etc/systemd/system/mc-backend.service > /dev/null << EOF
[Unit]
Description=Mission Control Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=azureuser
Group=azureuser
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Nginx config
sudo tee /etc/nginx/sites-available/mission-control > /dev/null << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name _;

    # Frontend (built React app)
    root /home/azureuser/Durgamma/frontend/dist;
    index index.html;

    # API proxy to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400s;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

# Enable site, disable default
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/mission-control /etc/nginx/sites-enabled/
sudo nginx -t

echo "  Systemd services configured."

# --- Start services ---
echo "[7/7] Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable mc-backend
sudo systemctl restart mc-backend
sudo systemctl restart nginx

# Wait for backend to start
echo "  Waiting for backend to start..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "  Backend is up!"
        break
    fi
    sleep 2
done

echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "  Backend:   http://20.119.62.230:8000/api/health"
echo "  Frontend:  http://20.119.62.230"
echo "  API Docs:  http://20.119.62.230/api/docs"
echo ""

# Quick health check
echo "Health check:"
curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || echo "  Backend starting up..."
echo ""
echo "Nginx status:"
sudo systemctl status nginx --no-pager -l | head -5
echo ""
echo "Backend status:"
sudo systemctl status mc-backend --no-pager -l | head -5
