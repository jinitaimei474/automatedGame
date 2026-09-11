param(
  [Parameter(Mandatory = $true)][string]$LastWeights,
  [string]$Device = 'cpu'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\train.py') --resume $LastWeights --device $Device

