$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath '.venv-win\Scripts\python.exe') {
  $backendPython = '.\.venv-win\Scripts\python.exe'
} elseif (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
  $backendPython = '.\.venv\Scripts\python.exe'
} elseif (Test-Path -LiteralPath '.venv\bin\python.exe') {
  $backendPython = '.\.venv\bin\python.exe'
} else {
  $backendPython = 'python'
}
$packageArgs = @('--noconfirm', '--clean', '--onefile', '--name', 'game-automation-backend', '--distpath', 'automation/dist', '--paths', '.')
$env:YOLO_CONFIG_DIR = Join-Path (Get-Location) 'build\ultralytics-config'
New-Item -ItemType Directory -Force -Path $env:YOLO_CONFIG_DIR | Out-Null
$env:MPLCONFIGDIR = Join-Path (Get-Location) 'build\matplotlib-config'
New-Item -ItemType Directory -Force -Path $env:MPLCONFIGDIR | Out-Null
& $backendPython -m PyInstaller @packageArgs automation/backend.py
if ($LASTEXITCODE -ne 0) { throw 'Python backend packaging failed' }
