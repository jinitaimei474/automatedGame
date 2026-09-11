from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, import_yolo, load_yaml, resolve_from_root


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="训练通用 Ultralytics YOLO 目标检测模型")
    command.add_argument("--config", default=str(ROOT / "config/train.yaml"), help="默认训练参数 YAML；命令行参数优先")
    command.add_argument("--data", default=str(ROOT / "dataset.yaml"))
    command.add_argument("--model", default="yolo11n.pt", help="预训练模型、last.pt 或模型 YAML")
    command.add_argument("--epochs", type=int, default=100)
    command.add_argument("--imgsz", type=int, default=640)
    command.add_argument("--batch", type=float, default=16, help="整数批量；-1 为自动批量")
    command.add_argument("--device", default="cpu", help="cpu、0、0,1 或 mps")
    command.add_argument("--workers", type=int, default=4)
    command.add_argument("--project", default=str(ROOT / "runs/train"))
    command.add_argument("--name", default="experiment")
    command.add_argument("--patience", type=int, default=30)
    command.add_argument("--cache", choices=("false", "ram", "disk"), default="false")
    command.add_argument("--optimizer", default="auto")
    command.add_argument("--lr0", type=float, default=0.01)
    command.add_argument("--seed", type=int, default=42)
    command.add_argument("--resume", nargs="?", const=True, default=False, help="不带值使用 model 续训，或提供 last.pt")
    command.add_argument("--no-pretrained", action="store_true")
    command.add_argument("--non-deterministic", action="store_true")
    command.add_argument("--close-mosaic", type=int, default=10)
    command.add_argument("--save-period", type=int, default=-1)
    command.add_argument("--exist-ok", action="store_true")
    return command


def main() -> None:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default=str(ROOT / "config/train.yaml"))
    pre_args, _ = pre_parser.parse_known_args()
    command = parser()
    config = load_yaml(pre_args.config) if pre_args.config else {}
    allowed = {action.dest for action in command._actions}
    defaults = {key: value for key, value in config.items() if key in allowed}
    if "pretrained" in config:
        defaults["no_pretrained"] = not bool(config["pretrained"])
    if "deterministic" in config:
        defaults["non_deterministic"] = not bool(config["deterministic"])
    command.set_defaults(**defaults)
    args = command.parse_args()
    YOLO = import_yolo()
    resume = args.resume
    model_path = args.model
    if isinstance(resume, str):
        model_path = str(resolve_from_root(resume))
        resume = True
    elif resume is True and Path(args.model).suffix.lower() == ".pt":
        candidate = resolve_from_root(args.model)
        model_path = str(candidate) if candidate.exists() else args.model
    cache: bool | str = False if args.cache in (False, "false") else args.cache
    batch = int(args.batch) if float(args.batch).is_integer() else args.batch
    model = YOLO(model_path)
    result = model.train(
        data=str(resolve_from_root(args.data)), epochs=args.epochs, imgsz=args.imgsz, batch=batch, device=args.device,
        workers=args.workers, project=str(resolve_from_root(args.project)), name=args.name, patience=args.patience,
        cache=cache, optimizer=args.optimizer, lr0=args.lr0, seed=args.seed, resume=resume,
        pretrained=not args.no_pretrained, deterministic=not args.non_deterministic, close_mosaic=args.close_mosaic,
        save_period=args.save_period, exist_ok=args.exist_ok, task="detect",
    )
    print(f"训练完成，结果目录: {result.save_dir}")


if __name__ == "__main__":
    main()
