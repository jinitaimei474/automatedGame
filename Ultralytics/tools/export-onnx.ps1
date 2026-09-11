param(
  [Parameter(Mandatory = $true)][string]$Weights,
  [int]$ImageSize = 640,
  [int]$Opset = 17,
  [switch]$Dynamic
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$arguments = @((Join-Path $root 'scripts\export.py'), '--weights', $Weights, '--format', 'onnx', '--imgsz', $ImageSize, '--opset', $Opset)
if ($Dynamic) { $arguments += '--dynamic' }
& (Join-Path $PSScriptRoot 'python.ps1') @arguments

