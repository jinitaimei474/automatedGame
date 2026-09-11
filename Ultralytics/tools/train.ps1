param(
  [string]$Model = 'yolo11n.pt',
  [int]$Epochs = 100,
  [int]$ImageSize = 640,
  [double]$Batch = 16,
  [string]$Device = 'cpu',
  [string]$Name = 'experiment'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\train.py') --model $Model --epochs $Epochs --imgsz $ImageSize --batch $Batch --device $Device --name $Name

