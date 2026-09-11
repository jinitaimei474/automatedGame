param(
  [double]$Train = 0.8,
  [double]$Val = 0.1,
  [double]$Test = 0.1,
  [int]$Seed = 42,
  [switch]$Clear
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$arguments = @((Join-Path $root 'scripts\split_dataset.py'), '--train', $Train, '--val', $Val, '--test', $Test, '--seed', $Seed)
if ($Clear) { $arguments += '--clear' }
& (Join-Path $PSScriptRoot 'python.ps1') @arguments

