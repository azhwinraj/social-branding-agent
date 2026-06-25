$root = $PSScriptRoot

Write-Host "Starting Social Branding Agent..." -ForegroundColor Cyan

# Start backend in a new terminal window
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Backend' -ForegroundColor Cyan; cd '$root\backend'; uv run uvicorn app.main:app --reload --port 8000"

# Start frontend in a new terminal window
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Frontend' -ForegroundColor Cyan; cd '$root\frontend'; npm run dev"

# Poll until backend is ready (max 30s)
Write-Host "Waiting for backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

if ($ready) {
    Write-Host "Backend ready. Opening browser..." -ForegroundColor Green
} else {
    Write-Host "Backend not responding after 30s — check the backend terminal for errors." -ForegroundColor Red
}

# Give frontend a moment then open browser regardless
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"
