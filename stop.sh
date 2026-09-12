#!/bin/bash
cd "$(dirname "$0")"
echo "🛑 Stopping QA Agent services..."
if [ -f .dashboard.pid ]; then
    kill $(cat .dashboard.pid) 2>/dev/null && echo "  Dashboard stopped."
    rm .dashboard.pid
fi
if command -v lsof &>/dev/null; then
    lsof -ti:8500 | xargs kill -9 2>/dev/null
elif command -v powershell.exe &>/dev/null; then
    powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort 8500 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }" 2>/dev/null
fi
echo "✅ Done."
