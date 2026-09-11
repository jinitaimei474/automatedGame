$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') -m pytest (Join-Path $root 'tests') -q

