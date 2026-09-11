# 环境、GitHub 同步与新设备恢复指南

本文说明如何在一台全新的 Windows 10/11 设备上，从私有 GitHub 仓库恢复 Game Automation Hub 的开发环境，并明确哪些大文件不会进入 Git。

## 1. 仓库中包含什么

仓库应包含：

- Electron、React、TypeScript 前端和主进程源码；
- Python 自动化后端、ADB、视觉检测、安全保护和工作流源码；
- Python 与前端测试；
- 训练、验证、导出和预标注脚本；
- YOLO 类别定义、预标注文本标签、复核队列和说明文档；
- `package-lock.json`、`requirements.txt`、`pyproject.toml` 等可重建依赖的文件；
- Codex 项目交接与对话纪要。

仓库不会包含：

- `node_modules/`、`.venv/`、`.venv-win/` 等可重建依赖；
- `dist/`、`build/`、`release/`、`automation/dist/` 等构建产物；
- `.pt`、`.onnx` 模型权重及训练 `runs/`；
- `task-results/`、日志、调试截图和运行时缓存；
- `datasets/raw/` 中的第三方视频和原始截图；
- `prelabels_gpt56sol/images/` 中约 621 MB 的复核图片；
- 正式训练集的图片和标签内容。

这些文件被排除，是因为它们体积较大、可重新生成、包含机器本地状态，或可能涉及第三方素材。Git 中保留目录结构和文字元数据，便于另一台设备理解并恢复工作。

## 2. 新设备克隆仓库

安装 Git 后执行：

```powershell
Set-Location C:\Users\你的用户名\Documents
git clone https://github.com/jinitaimei474/automatedGame.git
Set-Location automatedGame
```

确认分支和状态：

```powershell
git branch --show-current
git status
git log --oneline -5
```

## 3. 安装基础软件

建议准备：

- Windows 10/11；
- Git；
- Node.js 20 或更高版本；
- Anaconda 或 Miniconda；
- VS Code 与 Microsoft Python 扩展；
- 可选：MuMu 模拟器及可用的 Android `adb.exe`；
- 可选：支持 CUDA 的 NVIDIA 驱动，用于 GPU 训练。

确认版本：

```powershell
git --version
node --version
npm --version
conda --version
```

## 4. 创建项目 Python 环境

项目在 `pyproject.toml` 中要求 Python 3.11 或更高版本。为了兼容当前依赖，建议使用 Python 3.12：

```powershell
conda create -n automation python=3.12 pip -y
conda activate automation
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

验证解释器必须来自 Conda 环境：

```powershell
where.exe python
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version
```

正确路径应包含：

```text
envs\automation\python.exe
```

在 PowerShell 中应使用 `where.exe python`，而不是 `where python`；后者通常会被解释为 `Where-Object` 的别名。

如果环境提示符显示 `(automation)`，但找不到环境中的 `python.exe`，说明创建时可能只运行了 `conda create -n automation`。Conda 允许创建不含 Python 的空环境。可原地修复：

```powershell
conda install -n automation python=3.12 pip -y
```

如果 Conda 在普通 PowerShell 中无法激活：

```powershell
conda init powershell
```

随后关闭全部 PowerShell 和 VS Code 窗口并重新打开。

## 5. 在 VS Code 中选择解释器

1. 用 VS Code 打开仓库根目录。
2. 按 `Ctrl+Shift+P`。
3. 执行 `Python Environments: Refresh All Environment Managers`。
4. 执行 `Python: Select Interpreter`。
5. 选择名称包含 `automation` 的 Conda 环境。
6. 如果未显示，选择 `Enter interpreter path...`，手动选择 `envs\automation\python.exe`。
7. 新建终端并执行 `python -c "import sys; print(sys.executable)"` 验证。

## 6. 安装 Node.js 依赖并启动

```powershell
npm install
npm run dev
```

也可以运行项目脚本：

```powershell
.\scripts\dev.ps1
```

默认 `Mock` 模式不需要模型、模拟器或真实游戏账号，可先用它验证界面和工作流。

## 7. 本地配置

本机配置不进入 Git。首次使用时复制模板：

```powershell
Copy-Item config\settings.example.json config\settings.json
```

然后根据本机情况配置：

- MuMu 可执行文件；
- `adb.exe` 路径；
- 明确的模拟器设备序列号；
- 皇室战争包名和 Activity；
- 本机模型权重路径；
- 截图、推理和安全阈值。

不要把令牌、账号密码或其他凭据加入 `settings.json`，也不要强制提交该文件。

## 8. 恢复模型和数据集

正式模型应由安全的私有存储单独复制到：

```text
automation/games/clash_royale/models/best.pt
```

正式训练数据目录：

```text
automation/training/clash_royale/datasets/images/train
automation/training/clash_royale/datasets/images/val
automation/training/clash_royale/datasets/images/test
automation/training/clash_royale/datasets/labels/train
automation/training/clash_royale/datasets/labels/val
automation/training/clash_royale/datasets/labels/test
```

Git 中保留的 `prelabels_gpt56sol/labels/` 必须与恢复后的 `prelabels_gpt56sol/images/` 中同名图片配对。恢复后检查图片与标签数量：

```powershell
$root = "automation\training\clash_royale\datasets\prelabels_gpt56sol"
(Get-ChildItem "$root\images" -File).Count
(Get-ChildItem "$root\labels" -Filter "*.txt" -File | Where-Object Name -ne "classes.txt").Count
```

当前原设备预期均为 681。

## 9. LabelImg 稳定环境

LabelImg 1.8.6 较旧，不建议安装在项目 Python 3.12 环境中。在 Windows 上单独创建 Python 3.9 环境：

```powershell
conda create -n labelimg39 python=3.9 pip -y
conda activate labelimg39
python -m pip install "labelImg==1.8.6" "PyQt5==5.15.2" lxml
```

确认预标注目录中的类别文件同时存在于根目录和 `labels` 目录：

```powershell
$reviewRoot = "C:\你的仓库路径\automation\training\clash_royale\datasets\prelabels_gpt56sol"
Copy-Item "$reviewRoot\classes.txt" "$reviewRoot\labels\classes.txt" -Force
```

启动：

```powershell
labelImg "$reviewRoot\images" "$reviewRoot\classes.txt" "$reviewRoot\labels"
```

详细复核规则见 `docs/ANNOTATION_REVIEW.zh-CN.md`。审核后还需手动更新 `review_queue.csv` 中的 `review_status`、`reviewer` 和 `review_notes`。

## 10. 测试与构建

```powershell
npm run lint
npm run typecheck
npm run test
python -m pytest tests/python -q
```

全部检查：

```powershell
.\scripts\test.ps1
```

构建与打包见 `docs/PACKAGING.zh-CN.md`。

## 11. GitHub 日常同步

提交本地修改：

```powershell
git status
git add -A
git commit -m "描述本次修改"
git push
```

在另一台设备获取更新：

```powershell
git pull --ff-only
```

提交前应确认没有将模型、原始数据、构建产物、运行日志或本机配置加入暂存区：

```powershell
git status --short
git diff --cached --stat
```

## 12. 在另一台设备让 Codex 接手

克隆仓库后，可以把下面这段话直接发给 Codex：

```text
请先阅读 README.md、docs/CODEX_HANDOFF.zh-CN.md、
docs/ENVIRONMENT_AND_SYNC.zh-CN.md、docs/TRAINING.zh-CN.md 和
docs/ANNOTATION_REVIEW.zh-CN.md。检查当前 Git 状态和最近提交，不要假设大型图片、
视频、模型权重、运行日志或本机 settings.json 已包含在仓库中。先总结项目当前状态、
可运行模式、数据缺口和下一步建议，再根据我的新要求继续工作。
```

