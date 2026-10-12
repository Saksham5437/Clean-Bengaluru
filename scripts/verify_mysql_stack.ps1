param(
  [string]$EnvFile = '.env'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
  if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw "Environment file not found: $EnvFile. Copy .env.example to .env and replace every placeholder."
  }

  docker info --format '{{.ServerVersion}}' | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw 'Docker daemon is unavailable. Start Docker Desktop and run this script again.'
  }

  Write-Host 'Starting MySQL, API and web services...'
  docker compose --env-file $EnvFile -f infra/docker-compose.yml up -d --build

  $ready = $false
  for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
      $response = Invoke-RestMethod 'http://127.0.0.1:8000/ready'
      if ($response.status -eq 'ready' -and $response.database -eq 'mysql') {
        $ready = $true
        $response | ConvertTo-Json -Compress
        break
      }
    } catch { }
    Start-Sleep -Seconds 2
  }

  if (-not $ready) {
    docker compose --env-file $EnvFile -f infra/docker-compose.yml ps
    throw 'The API did not become MySQL-ready within 60 seconds.'
  }

  Write-Host 'MySQL-backed stack is ready.' -ForegroundColor Green
} finally {
  Pop-Location
}
