from __future__ import annotations

import argparse
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    base = Path(__file__).parent
    p = argparse.ArgumentParser(description="训练皇室战争 YOLO 检测模型")
    p.add_argument("--data", default=str(base / "dataset.yaml"))
    p.add_argument("--model", default="yolo11n.pt")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=960)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--device", default="cpu")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--project", default=str(base / "runs"))
    p.add_argument("--name", default="clash_royale")
    p.add_argument("--resume", nargs="?", const=True, default=False)
    return p


def main() -> None:
    args = parser().parse_args()
    from ultralytics import YOLO
    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
                workers=args.workers, project=args.project, name=args.name, resume=args.resume)


if __name__ == "__main__":
    main()

