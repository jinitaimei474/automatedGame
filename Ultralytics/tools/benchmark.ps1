param(
  [Parameter(Mandatory = $true)][string]$Weights,
  [Parameter(Mandatory = $true)][string]$Source,
  [string]$Device = 'cpu',
  [int]$Runs = 50
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\benchmark.py') --weights $Weights --source $Source --device $Device --runs $Runs

