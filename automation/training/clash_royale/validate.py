from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    base = Path(__file__).parent
    parser = argparse.ArgumentParser(description="验证皇室战争 YOLO 模型")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", default=str(base / "dataset.yaml"))
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    from ultralytics import YOLO
    metrics = YOLO(args.weights).val(data=args.data, imgsz=args.imgsz, device=args.device, plots=True)
    print(metrics.results_dict)


if __name__ == "__main__":
    main()

