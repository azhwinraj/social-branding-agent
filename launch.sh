#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Social Branding Agent"
echo "---------------------"

# Check dependencies
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found. Install Python 3.12+ from python.org"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found. Install Node.js 18+ from nodejs.org"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "ERROR: uv not found. Run: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

# First-run: install backend deps
if [ ! -d "$ROOT/backend/.venv" ]; then
    echo "Installing backend dependencies (first run)..."
    cd "$ROOT/backend" && uv sync && cd "$ROOT"
fi

# First-run: install frontend deps
if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "Installing frontend dependencies (first run)..."
    cd "$ROOT/frontend" && npm install --silent && cd "$ROOT"
fi

# First-run: bootstrap .env
if [ ! -f "$ROOT/.env" ]; then
    if [ -f "$ROOT/.env.example" ]; then
        cp "$ROOT/.env.example" "$ROOT/.env"
        echo ""
        echo "  .env created. Open it and add at least GROQ_API_KEY, then re-run this script."
        echo ""
        exit 0
    fi
fi

# Apply pending DB migrations
cd "$ROOT/backend" && uv run alembic upgrade head 2>/dev/null && cd "$ROOT"

# Start backend
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/backend' && uv run uvicorn app.main:app --reload --port 8000\""
else
    gnome-terminal -- bash -c "cd '$ROOT/backend' && uv run uvicorn app.main:app --reload --port 8000; exec bash" 2>/dev/null || \
    xterm -e "cd '$ROOT/backend' && uv run uvicorn app.main:app --reload --port 8000" &
fi

# Start frontend
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/frontend' && npm run dev\""
else
    gnome-terminal -- bash -c "cd '$ROOT/frontend' && npm run dev; exec bash" 2>/dev/null || \
    xterm -e "cd '$ROOT/frontend' && npm run dev" &
fi

# Wait for backend then open browser
echo "Waiting for backend to be ready..."
until curl -s http://localhost:8000/api/health >/dev/null 2>&1; do sleep 2; done

if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:5173"
else
    xdg-open "http://localhost:5173" 2>/dev/null || echo "Open http://localhost:5173 in your browser"
fi

echo ""
echo "Running at http://localhost:5173"
echo "Close the terminal windows to stop."
