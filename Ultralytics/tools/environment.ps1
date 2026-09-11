param([switch]$RequireCuda)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$arguments = @((Join-Path $root 'scripts\check_environment.py'))
if ($RequireCuda) { $arguments += '--require-cuda' }
& (Join-Path $PSScriptRoot 'python.ps1') @arguments

