param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PythonArgs)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
  throw '训练环境不存在，请先运行 tools/setup.ps1'
}
$env:YOLO_CONFIG_DIR = Join-Path $root '.runtime\ultralytics'
$env:MPLCONFIGDIR = Join-Path $root '.runtime\matplotlib'
& $venvPython @PythonArgs
exit $LASTEXITCODE

