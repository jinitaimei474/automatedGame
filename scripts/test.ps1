$ErrorActionPreference = 'Stop'
npm run lint
npm run typecheck
npm run test
if (Test-Path -LiteralPath '.venv-win\Scripts\python.exe') {
  .\.venv-win\Scripts\python.exe -m pytest tests/python -q
} elseif (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
  .\.venv\Scripts\python.exe -m pytest tests/python -q
} elseif (Test-Path -LiteralPath '.venv\bin\python.exe') {
  .\.venv\bin\python.exe -m pytest tests/python -q
} else {
  python -m pytest tests/python -q
}
