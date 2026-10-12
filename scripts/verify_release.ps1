$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
  $venvPython = Join-Path $repoRoot 'backend/.venv/Scripts/python.exe'
  $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

  Write-Host 'Running backend tests...'
  Push-Location backend
  try { & $python -m pytest -q tests } finally { Pop-Location }

  Write-Host 'Building the frontend...'
  Push-Location frontend
  try { npm run build } finally { Pop-Location }

  Write-Host 'Validating Docker Compose configuration...'
  docker compose --env-file .env.example -f infra/docker-compose.yml config --quiet

  Write-Host 'Release verification passed.' -ForegroundColor Green
} finally {
  Pop-Location
}
