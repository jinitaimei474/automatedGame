# Windows 打包指南

## 前置条件

- Windows 10/11、Node.js 20+、Python 3.11+。
- `npm install` 和 `python -m pip install -r requirements.txt` 已完成。
- 如使用正式视觉模型，把 `best.pt` 放到 `automation/games/clash_royale/models`。

## 构建

```powershell
.\scripts\package-python.ps1
npm run build
.\scripts\package-windows.ps1
```

Python 单文件程序输出到 `automation/dist/game-automation-backend.exe`。Electron 前端输出到 `dist`，主进程输出到 `dist-electron`，NSIS 安装包输出到 `release`。

打包后用户配置写入 Electron 的 `userData/config/settings.json`，不会覆盖安装目录。卸载或升级不会主动关闭/删除用户已有的 MuMu 实例和模型外数据。

