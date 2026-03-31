param(
  [switch]$DryRun,
  [string[]]$CardUid = @()
)

$commandArgs = @("exec", "beer_backend_api", "python", "/app/dev_db_cleanup.py")

if ($DryRun) {
  $commandArgs += "--dry-run"
}

foreach ($uid in $CardUid) {
  $commandArgs += "--card"
  $commandArgs += $uid
}

& docker @commandArgs
exit $LASTEXITCODE
