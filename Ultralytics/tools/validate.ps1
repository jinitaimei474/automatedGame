param(
  [Parameter(Mandatory = $true)][string]$Weights,
  [string]$Device = 'cpu',
  [ValidateSet('val', 'test', 'train')][string]$Split = 'val'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\validate.py') --weights $Weights --device $Device --split $Split

