# 皇室战争 YOLO 训练指南

运行时优先识别完整的结算结果类别 `result_crowns_0`～`result_crowns_3`，`result_crown_active` / `result_crown_inactive` 用作后续交叉校验。这样能把皇冠统计限制在明确的结算页面语境内。项目没有附带虚构权重或准确率。

## 环境与目录

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

数据必须放在以下固定目录，图片与同名 `.txt` YOLO 标签一一对应：

```text
automation/training/clash_royale/datasets/images/train
automation/training/clash_royale/datasets/images/val
automation/training/clash_royale/datasets/images/test
automation/training/clash_royale/datasets/labels/train
automation/training/clash_royale/datasets/labels/val
automation/training/clash_royale/datasets/labels/test
```

原始视频或未整理截图可放在 `datasets/raw`。使用 CVAT、Label Studio 或 labelImg 导出 YOLO 格式。`dataset.yaml` 是唯一的类别 ID 映射来源，共 34 类；修改类别时必须同步运行时代码和本文档。

## 采集与标注规范

- 覆盖不同设备分辨率、横竖屏变化、游戏语言、明暗主题、动画阶段和网络质量；保留真实比例，不拉伸截图。
- 主页、模式列表、匹配、对局、胜利、失败、平局、奖励弹窗、商店及阻塞页面都要采集。免费物品需要同时标注 `daily_trader`、`free_item`、`free_label`；有价格时标注 `currency_price`。
- 对结算页分别收集 0、1、2、3 皇冠，并覆盖胜利、失败和平局。完整结果区域标注为 `result_crowns_N`；亮起或未亮起的单个皇冠可额外标注为 active/inactive。
- 部分遮挡但仍能可靠判断完整结果时标注；无法判断数量时不要硬标 `result_crowns_N`，可以只标可见的单皇冠。
- 不得把奖励皇冠、通行证皇冠或主页皇冠标成结算皇冠。只有对局结算语境才使用结果类别。
- 从视频抽帧时，以整段对局/录屏会话为组划分 train/val/test。禁止把连续相邻帧随机拆到不同集合，否则会产生数据泄漏。

推荐先按场景建立采集清单，再标注 300～500 张多样化初始样本；看混淆矩阵补齐弱类，而不是只堆相似帧。

## 检查、训练、续训与验证

```powershell
python automation/training/clash_royale/check_dataset.py
python automation/training/clash_royale/train.py --data automation/training/clash_royale/dataset.yaml --model yolo11n.pt --epochs 100 --imgsz 960 --batch 8 --device 0 --workers 4 --project automation/training/clash_royale/runs --name cr-v1
python automation/training/clash_royale/train.py --resume automation/training/clash_royale/runs/cr-v1/weights/last.pt
python automation/training/clash_royale/validate.py --weights automation/training/clash_royale/runs/cr-v1/weights/best.pt --device 0
```

Ultralytics 输出的 `results.csv`、PR 曲线和 confusion matrix 位于对应 run 目录。评估皇冠时，除整体 mAP 外应单独查看 0～3 皇冠四类的 precision、recall 和混淆矩阵，并用完整未见过的结算录屏计算：

- 单帧分类正确率；
- 连续 N 帧确认后的对局级皇冠准确率；
- 重复统计率（目标为 0）；
- 未确认率和错误放行到下一局的次数（目标为 0）。

## 导出与部署

```powershell
python automation/training/clash_royale/export.py --weights automation/training/clash_royale/runs/cr-v1/weights/best.pt --imgsz 960 --opset 17 --dynamic
Copy-Item automation/training/clash_royale/runs/cr-v1/weights/best.pt automation/games/clash_royale/models/best.pt
```

可保留 PyTorch `best.pt`，也可把导出的 ONNX 复制到运行时模型目录。最后在应用设置页选择模型并依次执行“测试模型”和“测试皇冠识别”。

