param(
  [Parameter(Mandatory = $true)]
  [string] $DatabaseUrl,

  [Parameter(Mandatory = $true)]
  [string] $TenantId,

  [Parameter(Mandatory = $true)]
  [string] $OrganisationId,

  [Parameter(Mandatory = $true)]
  [string] $RapportId,

  [int] $DurationSeconds = 300,
  [int] $Clients = 8,
  [int] $Threads = 4
)

$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $PSScriptRoot "pgbench-dashboard-query.sql"

pgbench `
  -n `
  -M prepared `
  -T $DurationSeconds `
  -c $Clients `
  -j $Threads `
  -P 10 `
  -r `
  -D "tenant_id='$TenantId'" `
  -D "organisation_id='$OrganisationId'" `
  -D "rapport_id='$RapportId'" `
  -f $ScriptPath `
  $DatabaseUrl

Write-Host ""
Write-Host "Target VERIDIS: latency p95 < 100 ms for dashboard_esrs query."
Write-Host "If pgbench output only gives average latency, pair this run with application histogram monitoring."
