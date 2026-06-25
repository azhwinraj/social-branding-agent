$root = $PSScriptRoot
$ErrorActionPreference = "Stop"

function Check-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$name' not found. $hint" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Social Branding Agent" -ForegroundColor Cyan
Write-Host "---------------------" -ForegroundColor DarkGray

# Dependency checks
Check-Command "python" "Install Python 3.12+ from python.org"
Check-Command "node" "Install Node.js 18+ from nodejs.org"
Check-Command "uv" "Install uv: powershell -c 'irm https://astral.sh/uv/install.ps1 | iex'"

# First-run: install frontend deps if missing
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    npm install --silent
    Pop-Location
}

# First-run: copy .env if missing
if (-not (Test-Path "$root\.env")) {
    if (Test-Path "$root\.env.example") {
        Copy-Item "$root\.env.example" "$root\.env"
        Write-Host "Created .env from .env.example — add your API keys before generating drafts." -ForegroundColor Yellow
    }
}

# First-run: apply DB migrations
Push-Location "$root\backend"
uv run alembic upgrade head 2>$null
Pop-Location

Write-Host "Starting backend..." -ForegroundColor Yellow
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host '[Backend]' -ForegroundColor Cyan; cd '$root\backend'; uv run uvicorn app.main:app --reload --port 8000" `
    -PassThru

Write-Host "Starting frontend..." -ForegroundColor Yellow
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host '[Frontend]' -ForegroundColor Cyan; cd '$root\frontend'; npm run dev" `
    -PassThru

# Poll until backend is ready (max 30s)
Write-Host "Waiting for backend to be ready..." -ForegroundColor DarkGray
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

if ($ready) {
    Write-Host "Ready. Opening browser..." -ForegroundColor Green
} else {
    Write-Host "Backend not responding after 30s. Check the backend terminal for errors." -ForegroundColor Red
}

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Running at http://localhost:5173" -ForegroundColor Cyan
Write-Host "Close both terminal windows to stop." -ForegroundColor DarkGray
