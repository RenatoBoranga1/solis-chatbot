$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [string[]]$Arguments
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Comando falhou com exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
  }
}

function Assert-Contains {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Content,
    [Parameter(Mandatory = $true)]
    [string]$Needle
  )

  if (-not $Content.Contains($Needle)) {
    throw "Roteiro E2E nao contem marcador obrigatorio: $Needle"
  }
}

Write-Host "==> Validando roteiro manual E2E"
$guidePath = Join-Path (Get-Location) "docs\e2e-test-solis.md"
if (-not (Test-Path $guidePath)) {
  throw "Arquivo docs/e2e-test-solis.md nao encontrado."
}
$guideContent = Get-Content $guidePath -Raw -Encoding UTF8
@(
  "docker compose up --build",
  "Invoke-RestMethod http://localhost:8000/health",
  "Diagnostico",
  "Modo demonstracao",
  "LGPD",
  "Upload da conta",
  "Parser CPFL",
  "Aplicar ao lead",
  "Link seguro",
  "Tentar reconectar"
) | ForEach-Object { Assert-Contains -Content $guideContent -Needle $_ }

Write-Host "==> Subindo Docker Compose"
Invoke-Checked -Command "docker" -Arguments @("compose", "up", "-d", "--build")

Write-Host "==> Verificando backend /health"
$health = Invoke-RestMethod http://localhost:8000/health
if ($health.status -ne "ok") {
  throw "Backend /health nao retornou status ok."
}
$health | ConvertTo-Json -Compress

Write-Host "==> Verificando frontend"
$frontendStatus = (Invoke-WebRequest http://localhost:5173 -UseBasicParsing).StatusCode
if ($frontendStatus -ne 200) {
  throw "Frontend nao respondeu HTTP 200."
}

Write-Host "==> Rodando testes do backend no container"
Invoke-Checked -Command "docker" -Arguments @("compose", "run", "--rm", "backend", "python", "-m", "unittest", "discover", "tests")

Write-Host "==> Validando SQL das migrations"
$migrationSqlPath = Join-Path $env:TEMP "solis-alembic-upgrade.sql"
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& docker @("compose", "run", "--rm", "backend", "alembic", "upgrade", "head", "--sql") > $migrationSqlPath 2>&1
$migrationExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($migrationExitCode -ne 0) {
  Get-Content $migrationSqlPath -Tail 120
  throw "Falha ao gerar SQL das migrations. Veja $migrationSqlPath"
}

Write-Host "==> Rodando testes estaticos do frontend no container"
Invoke-Checked -Command "docker" -Arguments @("compose", "run", "--rm", "frontend", "npm", "test")

Write-Host "==> Smoke E2E concluido. Execute docs/e2e-test-solis.md para a validacao visual/manual completa."
