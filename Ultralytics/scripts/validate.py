from __future__ import annotations

import argparse

from common import ROOT, import_yolo, resolve_from_root


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 YOLO 检测模型并生成 PR 曲线和混淆矩阵")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", default=str(ROOT / "dataset.yaml"))
    parser.add_argument("--split", choices=("val", "test", "train"), default="val")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf", type=float, default=0.001)
    parser.add_argument("--iou", type=float, default=0.6)
    parser.add_argument("--project", default=str(ROOT / "runs/val"))
    parser.add_argument("--name", default="validation")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()
    YOLO = import_yolo()
    model = YOLO(str(resolve_from_root(args.weights)))
    metrics = model.val(data=str(resolve_from_root(args.data)), split=args.split, imgsz=args.imgsz, batch=args.batch,
                        device=args.device, conf=args.conf, iou=args.iou, plots=True, save_json=args.save_json,
                        project=str(resolve_from_root(args.project)), name=args.name, task="detect")
    print(f"mAP50: {metrics.box.map50:.6f}")
    print(f"mAP50-95: {metrics.box.map:.6f}")
    print(f"结果目录: {metrics.save_dir}")


if __name__ == "__main__":
    main()

