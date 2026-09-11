param(
  [Parameter(Mandatory = $true)][string]$Weights,
  [Parameter(Mandatory = $true)][string]$Source,
  [string]$Device = 'cpu',
  [double]$Confidence = 0.25
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\predict.py') --weights $Weights --source $Source --device $Device --conf $Confidence

