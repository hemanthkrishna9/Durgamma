#!/bin/bash
# Mission Control — One-click installer
# Sets up the backend and frontend for local development

set -e

echo "========================================"
echo "  Mission Control — AI Agent Squad Platform"
echo "========================================"
echo ""

# Check prerequisites
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed. Please install it first."
        exit 1
    fi
}

echo "Checking prerequisites..."
check_command python3
check_command node
check_command npm
check_command git

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python: $PYTHON_VERSION"
echo "  Node: $(node --version)"
echo "  npm: $(npm --version)"
echo ""

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Setup Backend
echo "Setting up backend..."
cd "$PROJECT_ROOT/backend"

if [ ! -d "venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "  Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "  Backend setup complete."
echo ""

# Setup Frontend
echo "Setting up frontend..."
cd "$PROJECT_ROOT/frontend"

echo "  Installing Node dependencies..."
npm install --silent

echo "  Frontend setup complete."
echo ""

# Create .env if it doesn't exist
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    echo "Creating .env file..."
    cat > "$PROJECT_ROOT/backend/.env" << 'ENVEOF'
# Mission Control Configuration
MC_DEBUG=true
MC_DATABASE_URL=sqlite+aiosqlite:///./mission_control.db
MC_OPENCLAW_GATEWAY_URL=ws://localhost:18789
MC_ANTHROPIC_API_KEY=
MC_DEFAULT_MODEL=claude-sonnet-4-20250514
MC_MISSIONS_DIR=./missions
MC_AGENT_TEMPLATES_DIR=../agent-templates
ENVEOF
    echo "  .env created. Set MC_ANTHROPIC_API_KEY for LLM-powered features."
fi

# Create missions directory
mkdir -p "$PROJECT_ROOT/backend/missions"

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To start the backend:"
echo "  cd backend && source venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "Dashboard: http://localhost:5173"
echo "API docs:  http://localhost:8000/docs"
echo ""
