$ErrorActionPreference = 'Stop'
npm run package:win
if ($LASTEXITCODE -ne 0) { throw 'Windows installer packaging failed' }
Write-Host '安装包输出目录: release'

