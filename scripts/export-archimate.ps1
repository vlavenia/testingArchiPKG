param(
    [string]$Source = 'model',
    [string]$OutDir = 'exported_diagrams',
    [switch]$DryRun = $false
)

$python = $env:PYTHON_EXE
if (-not $python) {
    $python = 'python'
}

if ($DryRun) {
    & $python scripts/export_archimate.py --source $Source --outdir $OutDir --dry-run
}
else {
    & $python scripts/export_archimate.py --source $Source --outdir $OutDir
}
