from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys

from common import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 YOLO 训练环境、CUDA 和目录")
    parser.add_argument("--require-cuda", action="store_true", help="没有 CUDA 时以失败退出")
    args = parser.parse_args()
    print(f"项目目录: {ROOT}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"系统: {platform.platform()}")
    try:
        import torch
        import ultralytics
    except ImportError as exc:
        raise SystemExit(f"依赖缺失: {exc.name}。请运行 tools/setup.ps1") from exc
    print(f"Ultralytics: {ultralytics.__version__}")
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA 版本: {torch.version.cuda}")
        for index in range(torch.cuda.device_count()):
            print(f"GPU {index}: {torch.cuda.get_device_name(index)}")
    else:
        print("提示: 当前将使用 CPU；NVIDIA GPU 用户应安装匹配 CUDA 的 PyTorch。")
    if shutil.which("nvidia-smi"):
        subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], check=False)
    if args.require_cuda and not torch.cuda.is_available():
        raise SystemExit("未检测到 CUDA")


if __name__ == "__main__":
    main()

