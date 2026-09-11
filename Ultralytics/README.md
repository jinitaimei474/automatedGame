# 通用 Ultralytics YOLO 目标检测训练框架

这是一个独立、常规的 YOLO 目标检测工程，默认使用 Ultralytics YOLO11。它不绑定任何游戏或业务类别，支持：

- 自定义类别和 `dataset.yaml` 生成；
- 原始数据确定性划分；
- 图片、标签、坐标、类别和数据泄漏检查；
- CPU、单 GPU、多 GPU 训练与断点续训；
- 验证、混淆矩阵、PR 曲线、批量推理；
- ONNX、OpenVINO、TensorRT、TorchScript、CoreML、TFLite 和 NCNN 导出；
- 单张模型延迟基准测试；
- Windows PowerShell 一键命令和工具单元测试。

仓库不附带虚构数据集、训练权重或准确率。

## 目录

```text
Ultralytics/
  classes.txt                 每行一个类别
  dataset.yaml                Ultralytics 数据配置
  config/train.yaml           默认训练参数
  datasets/
    raw/images                未划分图片
    raw/labels                未划分 YOLO 标签
    images/{train,val,test}   已划分图片
    labels/{train,val,test}   已划分标签
  scripts/                    Python 命令行工具
  tools/                      PowerShell 一键脚本
  weights/                    预训练/部署权重
  runs/                       训练和验证输出
  predictions/                推理输出
  exports/                    模型导出目录
  tests/                      数据工具测试
```

## 1. 安装环境

在本目录打开 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\setup.ps1
.\tools\environment.ps1
```

默认 PyPI PyTorch 通常适合 CPU。NVIDIA GPU 用户应根据 [PyTorch 官方安装器](https://pytorch.org/get-started/locally/) 选择与驱动匹配的 CUDA 命令，在 `.venv` 中安装 GPU 版 PyTorch，再执行 `setup.ps1` 补齐其他依赖。

## 2. 定义类别

编辑 `classes.txt`，每行一个类别，顺序就是类别 ID：

```text
person
car
bicycle
```

生成配置：

```powershell
.\tools\make-dataset.ps1
```

不要在已标注或已训练后随意调换类别顺序。

## 3. 准备数据

将原始图片和同名 YOLO 标签分别放入：

```text
datasets/raw/images
datasets/raw/labels
```

然后执行：

```powershell
.\tools\split-dataset.ps1 -Train 0.8 -Val 0.1 -Test 0.1 -Seed 42
.\tools\check.ps1
```

重新划分并覆盖已有集合时显式添加 `-Clear`。默认复制原始文件，不会删除 raw 数据。详细标注规则见 [标注规范](docs/ANNOTATION_GUIDE.md)。也可以跳过自动划分，直接把数据放入 `images/train` 等目录。

## 4. 训练

CPU 快速验证：

```powershell
.\tools\train.ps1 -Model yolo11n.pt -Epochs 3 -ImageSize 640 -Batch 4 -Device cpu -Name smoke
```

单张 NVIDIA GPU：

```powershell
.\tools\train.ps1 -Model yolo11n.pt -Epochs 100 -ImageSize 640 -Batch 16 -Device 0 -Name detector-v1
```

更完整参数可直接调用 Python：

```powershell
.\tools\python.ps1 .\scripts\train.py --config .\config\train.yaml --model yolo11s.pt --epochs 200 --batch -1 --device 0 --name detector-v2
```

模型可选择 `yolo11n.pt`、`yolo11s.pt`、`yolo11m.pt`、`yolo11l.pt` 或 `yolo11x.pt`。模型越大通常精度潜力越高，但显存、训练时间和推理延迟也更高。

多 GPU 示例：

```powershell
.\tools\python.ps1 .\scripts\train.py --device 0,1 --batch 32 --epochs 100
```

训练输出位于 `runs/train/<name>`，主要文件：

```text
weights/best.pt     验证集指标最佳权重
weights/last.pt     最后一轮权重，可用于续训
results.csv         每轮指标
confusion_matrix.png
PR_curve.png
```

## 5. 断点续训

```powershell
.\tools\resume.ps1 -LastWeights .\runs\train\detector-v1\weights\last.pt -Device 0
```

续训会恢复优化器、学习率和轮次状态；不要用 `best.pt` 代替 `last.pt` 做严格断点恢复。

## 6. 验证与测试集评估

```powershell
.\tools\validate.ps1 -Weights .\runs\train\detector-v1\weights\best.pt -Device 0 -Split val
.\tools\validate.ps1 -Weights .\runs\train\detector-v1\weights\best.pt -Device 0 -Split test
```

重点同时查看 mAP50、mAP50-95、各类别 precision/recall、混淆矩阵和真实误检/漏检样本。

## 7. 推理

```powershell
.\tools\predict.ps1 -Weights .\runs\train\detector-v1\weights\best.pt -Source .\demo -Device 0 -Confidence 0.25
```

`Source` 可以是图片、目录、视频、URL 或摄像头编号 `0`。结果写入 `predictions`。

## 8. 导出 ONNX

```powershell
.\tools\export-onnx.ps1 -Weights .\runs\train\detector-v1\weights\best.pt -ImageSize 640 -Opset 17 -Dynamic
```

其他格式：

```powershell
.\tools\python.ps1 .\scripts\export.py --weights .\runs\train\detector-v1\weights\best.pt --format openvino
.\tools\python.ps1 .\scripts\export.py --weights .\runs\train\detector-v1\weights\best.pt --format engine --device 0 --half
```

TensorRT `engine` 必须在目标 NVIDIA 环境中导出。INT8 导出需要有代表性的校准数据。

## 9. 性能测试

```powershell
.\tools\benchmark.ps1 -Weights .\runs\train\detector-v1\weights\best.pt -Source .\demo\test.jpg -Device 0 -Runs 100
```

## 10. 工具测试

```powershell
.\tools\test.ps1
```

遇到问题时先运行 `tools/environment.ps1` 和 `tools/check.ps1`。训练前应保证数据检查无错误；空数据集只能验证目录和脚本，不能开始有效训练。

