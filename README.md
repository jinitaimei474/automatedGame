# Game Automation Hub

Game Automation Hub 是一个面向 Windows 的插件式游戏自动化桌面应用。当前提供《皇室战争》经典 1v1 连续对局任务和每日商人免费物品任务；默认以 Mock 模式运行，不需要真实账号、模型或模拟器即可验证 UI、状态机、皇冠累计、去重与自动停止。

> 安全边界：项目不实现反检测、验证码绕过或反作弊规避。检测到登录、网络异常、未知阻塞页、价格或支付确认时会暂停。每日商人只有在同时识别 `daily_trader`、`free_item` 和 `free_label` 时才允许领取。

## 快速开始

```powershell
npm install
python -m pip install pytest
.\scripts\dev.ps1
```

如果使用 Anaconda，建议为项目建立 Python 3.12 环境；LabelImg 请使用单独的 Python 3.9 环境，避免旧版 PyQt 在 Windows 上闪退。完整的新设备安装、配置、数据恢复和 LabelImg 复核步骤见 [环境与跨设备恢复指南](docs/ENVIRONMENT_AND_SYNC.zh-CN.md)。

打开“游戏与功能”，选择经典 1v1，确认目标皇冠（默认 10）。若想快速演示，可输入 5：Mock 场景依次获得 1、2、2，累计 5 后进入 `TARGET_REACHED`，不会启动第四局。目标为 5 且对局脚本为 3、3 时会显示真实值 6/5，而进度条封顶 100%。

## 工程结构

```text
apps/desktop/src/main       Electron 主进程、Python 生命周期、IPC
apps/desktop/src/renderer   React + Mantine 深色控制台 UI
apps/desktop/src/shared     有类型的前后端消息协议
automation/core             ADB、模拟器、视觉、动作、安全、工作流、任务会话
automation/games            游戏插件与独立任务
automation/training         YOLO 数据集、训练、验证和导出
config                      用户可编辑设置
tests/python                无真实账号依赖的后端测试
docs                        训练与打包说明
scripts                     一键开发、测试和打包脚本
```

新增游戏只需注册新的 `GamePlugin`；新增任务通过 `TaskDefinition` 和 `TaskParameter` 声明，不需要在皇室战争 UI 中硬编码参数。

## 命令

```powershell
npm run dev          # Vite + Electron + Python 后端
npm run lint
npm run typecheck
npm run test         # 前端组件测试
python -m pytest tests/python -q
.\scripts\test.ps1   # 全部检查
npm run build        # 生产构建
.\scripts\package-windows.ps1
```

## 真实设备配置

在设置页填写 MuMu、`adb.exe`、明确的设备序列号、包名/Activity 和模型路径。多设备时必须填写目标序列号，应用不会随机选择。保存设置后重启应用，再使用“测试连接”“测试截图”“测试启动游戏”和“测试模型”。ADB 截图使用 `exec-out screencap -p`；路径通过参数数组传递，可处理空格和中文。

正式模型放置位置：

```text
automation/games/clash_royale/models/best.pt
```

训练图片与标签位置、标注规范、续训/验证/ONNX 导出见 [中文训练指南](docs/TRAINING.zh-CN.md)。Windows 安装包步骤见 [打包指南](docs/PACKAGING.zh-CN.md)。

## 在另一台设备继续使用 Codex

仓库包含一份面向人和 Codex 的持续交接文档：[Codex 项目交接与对话纪要](docs/CODEX_HANDOFF.zh-CN.md)。在新设备克隆仓库后，让 Codex 先阅读该文件、本文档以及 `docs/` 下的专题说明，即可恢复当前项目背景、已完成工作、数据状态和后续优先级。

本地 Codex 的完整原始任务记录不是项目源码的一部分，官方文档也没有确认本地任务历史可随 Git 仓库自动跨设备同步。因此仓库保存的是经过整理、可维护且不包含隐藏推理、令牌或机器缓存的对话纪要。若将来手动生成 Codex 分享链接，应注意链接可能扩大对话可见范围，不应把它当作私有仓库附件使用。

## 可靠性设计

- 所有状态变更通过 EventBus 推送；等待、重试和滑动均有上限并检查统一取消令牌。
- `CrownResultDetector` 仅接受 0～3，要求连续多帧一致；不一致不猜测。
- `CrownProgressTracker` 用唯一 `resultId` 去重，统一判断局数目标是否完成；旧皇冠模式保留兼容。
- 达标分支直接进入 `TARGET_REACHED`，取消后续动作，不进入 `START_NEXT_ROUND`。
- 任务结果保存到 `task-results/<sessionId>.json`。新建任务始终从 0 开始，不静默恢复旧进度。

## 当前限制

真实 1v1 已加入模板/颜色识别与固定卡组规则出牌，支持结算后继续下一局，完成启动时填写的目标局数后停止。默认 Mock 保留；YOLO 可作为兼容识别后端。

首次真实运行需要校准本机截图、八张卡牌、圣水采样区域和出牌落点，见 [免训练对局配置](docs/RULE_BATTLE.zh-CN.md)。不需要制作 YOLO 标注数据集。仓库的 `assets/clash_royale/` 附带本次 MuMu 国服校准模板，安装包首次运行会复制到用户配置目录；其他卡组或界面需要重新校准。连续两局实机验收见 [测试记录](docs/CLASH_REAL_DEVICE_TEST.zh-CN.md)。
