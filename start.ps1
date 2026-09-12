# Windows PowerShell equivalent of start.sh
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host "QA Agent Orchestration - Swag Labs Demo  (target: https://www.saucedemo.com/)"

if (-not (Test-Path .venv)) { python -m venv .venv }
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path node_modules)) {
    npm install
    npx playwright install chromium
}
& $py -c "import langgraph" 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install -r requirements.txt }

$proc = Start-Process -FilePath $py -ArgumentList '-m', 'uvicorn', 'dashboard.server:app', '--host', '127.0.0.1', '--port', '8500' -WindowStyle Hidden -PassThru
$proc.Id | Out-File -Encoding ascii .dashboard.pid
Start-Sleep -Seconds 2
Start-Process 'http://localhost:8500'

Write-Host ""
Write-Host "Dashboard running at http://localhost:8500 (PID $($proc.Id))"
Write-Host "Next:  .\.venv\Scripts\python.exe main.py"
Write-Host "Headless:  `$env:HEADED='false'; .\.venv\Scripts\python.exe main.py"
Write-Host "Stop:  .\stop.ps1"
