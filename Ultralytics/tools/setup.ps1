$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
  $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
  if ($pythonCommand) {
    & py -3 -m venv (Join-Path $root '.venv')
  } else {
    & python -m venv (Join-Path $root '.venv')
  }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root 'requirements.txt')
Write-Host "环境安装完成: $venvPython"

