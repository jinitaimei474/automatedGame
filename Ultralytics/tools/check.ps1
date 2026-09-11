param([switch]$Strict)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$arguments = @((Join-Path $root 'scripts\check_dataset.py'))
if ($Strict) { $arguments += '--strict' }
& (Join-Path $PSScriptRoot 'python.ps1') @arguments

