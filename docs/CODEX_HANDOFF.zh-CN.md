> 2026-10-29 更新：v0.2.0 已改为模板/颜色识别与固定卡组规则，启动填写目标对局数，连续匹配至完成。MuMu 实机连续两局无人工干预通过。模板位于 `assets/clash_royale/`；详见 [免训练配置](RULE_BATTLE.zh-CN.md)、[实测记录](CLASH_REAL_DEVICE_TEST.zh-CN.md) 和 [打包说明](PACKAGING.zh-CN.md)。下方早期 YOLO/MVP 记录仅作历史背景。

# Codex 项目交接与对话纪要

更新时间：2026-09-11（Asia/Shanghai）

本文是供项目维护者和另一台设备上的 Codex 阅读的持续交接文件。它记录用户可见的关键对话、已经验证的事实、设计边界和建议的下一步，不包含模型隐藏推理、访问令牌、浏览器凭据、虚拟环境或 Codex 本机缓存。

## 1. 项目目标

Game Automation Hub 是一个 Windows 桌面应用，使用 Electron + React 提供界面，使用 Python 后端负责模拟器、ADB、视觉检测、安全判断和任务工作流。

当前重点游戏是《皇室战争》，包含：

- 经典 1v1 皇冠目标任务；
- 每日商人免费物品任务；
- Mock 模式下的完整流程演示；
- 正式模式下的 MuMu/ADB、YOLO 检测、状态机、安全二次确认和结果记录；
- 训练、验证、导出、数据检查和预标注工具。

安全边界：不得实现反检测、验证码绕过或反作弊规避；检测到支付、价格、登录、网络异常或未知阻塞页时应暂停。真实模型和设备行为必须人工验收。

## 2. 当前代码结构

```text
apps/desktop/src/main       Electron 主进程、Python 生命周期、IPC
apps/desktop/src/renderer   React + Mantine 用户界面
apps/desktop/src/shared     前后端类型与协议
automation/core             ADB、模拟器、视觉、安全、事件与工作流
automation/games            游戏插件及任务实现
automation/training         YOLO 数据准备、训练、验证和导出
config                      配置模板与本机配置
tests                       Python 和前端测试
docs                        训练、标注、打包、环境和交接文档
scripts                     开发、测试和打包脚本
```

Python 版本要求在 `pyproject.toml` 中定义为 `>=3.11`。前端依赖和脚本以 `package.json`、`package-lock.json` 为准。

## 3. 预标注数据状态

预标注目录：

```text
automation/training/clash_royale/datasets/prelabels_gpt56sol
```

在原设备上已确认：

- 图片：681 张；
- YOLO 标签文件：681 个同名 `.txt`，另有 `classes.txt`；
- 草稿框：824 个；
- 至少有一个框的图片：663 张；
- 空标签图片：18 张；
- 类别：34 类；
- 全部图片初始审核状态：`pending`；
- 已对 681 个标签文件进行语法检查，未发现字段数量错误、类别越界或归一化坐标越界。

这些标签只是预标注，不是最终训练真值。必须按照 `docs/ANNOTATION_REVIEW.zh-CN.md` 逐图检查，并在 `review_queue.csv` 中记录 `approved`、`corrected` 或 `rejected`。

GitHub 仓库保存标签和文字元数据，不保存约 621 MB 的预标图片。新设备必须从可信的私有存储恢复图片，且图片文件名必须与标签文件名一致。

## 4. 对话纪要

### 2026-09-01：VS Code 找不到 Conda 环境

用户说明已创建名为 `automation` 的 Anaconda 环境，但 VS Code 的解释器列表中没有显示。

结论与建议：

- 使用 `Python Environments: Refresh All Environment Managers` 重新扫描；
- 使用 `Python: Select Interpreter` 选择环境；
- 如果未发现，手动选择环境目录中的 `python.exe`；
- 用 `python -c "import sys; print(sys.executable)"` 验证实际解释器；
- Notebook 还需要单独选择 Kernel，并在需要时安装 `ipykernel`。

### 2026-09-01：PowerShell 中 `where python` 没有输出

结论：PowerShell 中的 `where` 通常是 `Where-Object` 别名，应使用：

```powershell
where.exe python
Get-Command python
```

### 2026-09-01：激活环境后仍只显示系统 Python

用户得到的路径包括 MSYS2 Python、全局 Python 3.13 和 WindowsApps 启动别名，但没有 Conda 环境路径。

结论：这三个都不应作为 `automation` 环境解释器。需要检查：

```powershell
$env:CONDA_PREFIX
Test-Path "$env:CONDA_PREFIX\python.exe"
```

如果返回 `False`，说明环境中没有安装 Python。

### 2026-09-01：为什么 Conda 环境没有 Python

结论：`conda create -n automation` 可以创建空环境，不会自动继承 base 或系统 Python。提示符显示 `(automation)` 只证明环境被激活，不证明其中存在 Python。

项目要求 Python `>=3.11`，建议重新创建为：

```powershell
conda deactivate
conda env remove -n automation -y
conda create -n automation python=3.12 pip -y
conda activate automation
python -m pip install -r requirements.txt
```

### 2026-09-01：如何用 LabelImg 查看预标注及闪退原因

经检查发现：

- 预标注图片和标签位于 `prelabels_gpt56sol`；
- LabelImg 读取已有 YOLO `.txt` 时，会在标签文件所在目录查找 `classes.txt`；
- 当时 `labels/` 中缺少同目录 `classes.txt`，这是打开标签时的直接闪退风险；
- LabelImg 1.8.6 发布较早，Windows + Python 3.10 及更高版本存在 PyQt `drawLine`/浮点参数崩溃记录。

稳定方案是把类别文件复制到标签目录，并使用独立 Python 3.9 环境：

```powershell
Copy-Item prelabels_gpt56sol\classes.txt prelabels_gpt56sol\labels\classes.txt -Force
conda create -n labelimg39 python=3.9 pip -y
conda activate labelimg39
python -m pip install "labelImg==1.8.6" "PyQt5==5.15.2" lxml
labelImg <images目录> <classes.txt路径> <labels目录>
```

LabelImg 只负责修改框；审核状态仍需手动写入 `review_queue.csv`。

### 2026-09-11：同步到私有 GitHub 仓库

用户要求把项目和对话背景同步到私有仓库 `jinitaimei474/automatedGame`，便于另一台设备上的 Codex 接手。

同步前审计发现：

- 当前目录此前尚未初始化为 Git 仓库；
- 本机已配置 Git Credential Manager；
- 私有远端仓库存在且为空；
- 工作区约 4.8 万个文件，大部分是依赖、虚拟环境和生成物；
- `datasets/raw` 约 1.19 GB；
- `prelabels_gpt56sol/images` 约 621 MB；
- `automation/dist/game-automation-backend.exe` 约 278 MB；
- 未在拟提交的源码范围内发现明显 API key、访问令牌、私钥或密码文本。

因此采用标准源码仓库策略：提交可维护源码、锁文件、测试、配置模板、标签文本、复核元数据和文档；排除可重建依赖、二进制数据、模型、构建产物和运行时状态。

同步前于 2026-09-11 完成的验证结果：

- `npm run lint`：通过，0 个 ESLint 错误；
- `npm run typecheck`：通过，渲染进程和 Electron 主进程均无 TypeScript 类型错误；
- `npm test`：2 个测试文件、2 个测试全部通过；
- `python -m pytest tests/python -q`：31 个测试全部通过。

前端测试首次在受限沙箱中因 esbuild 无权读取父目录而无法加载 `vite.config.ts`；在获准的正常 Windows 环境中重新运行后全部通过。这是执行环境权限问题，不是项目测试失败。

## 5. 需要继续关注的问题

1. 681 张预标图片尚未进入 Git，需要单独备份和迁移。
2. 681 张预标注仍需人工复核，不能直接作为最终真值训练。
3. 正式模型权重没有进入 Git，需要在训练完成后单独保存。
4. 当前经典 1v1 策略是跟踪型 MVP，不负责自动出牌。
5. 正式模式需要在真实 MuMu 设备上人工验证 ADB、界面状态、模型阈值和安全暂停路径。
6. 训练、验证和测试集必须按视频或连续会话分组，避免相邻帧泄漏。

## 6. 建议的下一步顺序

1. 在 Mock 模式运行全部测试和桌面应用。
2. 单独备份 `datasets/raw`、预标图片和未来模型权重。
3. 使用 LabelImg 或更现代的标注工具完成 681 张人工复核。
4. 将审核后的数据按 `session_group` 划分 train/val/test。
5. 运行 `check_dataset.py`。
6. 训练 YOLO，并重点检查胜负、皇冠数量、免费/付费等易混淆类别。
7. 在未见过的完整录屏上做对局级验证。
8. 只有在安全暂停和二次确认均通过后，才在正式任务中使用模型。

## 7. 新 Codex 会话的建议首条消息

```text
请先阅读 README.md、docs/CODEX_HANDOFF.zh-CN.md、
docs/ENVIRONMENT_AND_SYNC.zh-CN.md、docs/TRAINING.zh-CN.md 和
docs/ANNOTATION_REVIEW.zh-CN.md。然后检查 Git 状态和最近提交，验证依赖是否安装，
总结当前可运行能力、缺失的大型本地资产、预标注审核进度和最安全的下一步。
未经我明确要求，不要上传数据集、模型、日志、本机配置或任何凭据。
```

## 8. 对话记录的边界

这份文件是结构化对话纪要，不是 Codex 本地数据库的原始导出。这样做有三个原因：

- Git 仓库需要保存与项目相关、可审阅、可长期维护的信息；
- 原始任务数据库可能包含工具输出、本机路径、缓存或其他不应上传的数据；
- 当前官方 OpenAI 文档未明确保证本地 Codex 任务历史会随 Git 仓库跨设备同步。

如果需要逐字保存未来的重要决策，应把用户可见的问题、结论和验证结果继续追加到本文，而不是提交 Codex 的本机缓存目录。
