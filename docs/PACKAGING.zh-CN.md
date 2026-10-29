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



## v0.2.0 发布说明

安装包包含 Python 后端、模板识别依赖及 `assets/clash_royale/` 的校准模板。安装包不包含本机 settings.json、账号截图、日志和训练数据。
首次启动使用 Mock 模式；在设置页选择 MuMu 的 adb.exe、设备序列号，确认国服包名和模板路径，保存后重启，再切换到真实模式。
安装后的运行目录使用 Electron userData（Windows 默认 `%APPDATA%/<应用名称>`），日志、配置及任务结果在此保存。已有配置与校准不会在升级时覆盖。

本次构建的下载与缓存目录为 `D:/automatedGame-build/cache`，临时目录为 `D:/automatedGame-build/temp`，安装包输出到 `D:/automatedGame-build/release`。
可通过 ELECTRON_CACHE、ELECTRON_BUILDER_CACHE、npm_config_cache、PIP_CACHE_DIR、PYINSTALLER_CONFIG_DIR、TEMP/TMP 指定这些路径。

发布前已直接运行冻结后的后端，验证 UTF-8 中文协议、模板加载和 Mock 连续两局自动完成。
