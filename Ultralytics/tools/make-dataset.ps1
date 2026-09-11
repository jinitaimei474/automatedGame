$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'python.ps1') (Join-Path $root 'scripts\make_dataset_yaml.py')

