#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "🚀 QA Agent Orchestration — Swag Labs Demo"
echo "   Target: https://www.saucedemo.com/"
echo ""

# --- Display check (visible browser requires a display server) ---
export HEADED=true
if [[ "$(uname)" == "Linux" ]] && [[ -z "$DISPLAY" ]] && [[ -z "$WAYLAND_DISPLAY" ]]; then
    echo "⚠️  No display server detected (no \$DISPLAY or \$WAYLAND_DISPLAY)."
    echo "   Browser tests will run HEADLESS. For visible execution,"
    echo "   run from a desktop environment or set DISPLAY."
    echo ""
    export HEADED=false
else
    echo "🖥️  Display detected — browser will be VISIBLE during tests"
fi

# --- Python venv (Scripts/ on Windows Git Bash, bin/ elsewhere) ---
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python venv..."
    (command -v python3 >/dev/null && python3 -m venv .venv) || python -m venv .venv
fi
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"; else PY=".venv/bin/python"; fi

# --- Install dependencies ---
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node dependencies..."
    npm install
    npx playwright install chromium --with-deps
fi

if ! "$PY" -c "import langgraph" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    "$PY" -m pip install -r requirements.txt
fi

# --- Start dashboard ---
echo "📊 Starting dashboard at http://localhost:8500..."
"$PY" -m uvicorn dashboard.server:app --host 127.0.0.1 --port 8500 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > .dashboard.pid
sleep 2

if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:8500
elif command -v open &>/dev/null; then
    open http://localhost:8500
elif command -v cmd.exe &>/dev/null; then
    cmd.exe /c start http://localhost:8500
fi

echo ""
echo "✅ Dashboard running at http://localhost:8500"
echo "   PID: $DASHBOARD_PID"
echo ""
echo "🔬 Next step — run the agent pipeline:"
echo "   $PY main.py"
echo ""
echo "   The browser will open VISIBLY and you'll watch it:"
echo "   • Navigate saucedemo.com"
echo "   • Fill in login forms"
echo "   • Click through products and checkout"
echo "   • Execute all 5 tests in real time"
echo ""
echo "   To run headless instead:  HEADED=false $PY main.py"
echo "   To stop everything:      ./stop.sh"
