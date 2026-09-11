from __future__ import annotations

import argparse

from common import ROOT, import_yolo, resolve_from_root


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 YOLO 模型批量预测图片、目录、视频、摄像头或 URL")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--source", required=True, help="图片/目录/视频/0（摄像头）/URL")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default=str(ROOT / "predictions"))
    parser.add_argument("--name", default="predict")
    parser.add_argument("--save-txt", action="store_true")
    parser.add_argument("--save-conf", action="store_true")
    parser.add_argument("--save-crop", action="store_true")
    parser.add_argument("--show-labels", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--show-conf", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--line-width", type=int, default=None)
    parser.add_argument("--exist-ok", action="store_true")
    args = parser.parse_args()
    YOLO = import_yolo()
    source = args.source if args.source.isdigit() else str(resolve_from_root(args.source)) if not args.source.startswith(("http://", "https://", "rtsp://")) else args.source
    results = YOLO(str(resolve_from_root(args.weights))).predict(
        source=source, imgsz=args.imgsz, conf=args.conf, iou=args.iou, device=args.device, save=True,
        save_txt=args.save_txt, save_conf=args.save_conf, save_crop=args.save_crop, show_labels=args.show_labels,
        show_conf=args.show_conf, line_width=args.line_width, project=str(resolve_from_root(args.project)),
        name=args.name, exist_ok=args.exist_ok, task="detect",
    )
    save_dir = results[0].save_dir if results else resolve_from_root(args.project) / args.name
    print(f"预测完成，共 {len(results)} 个输入，结果目录: {save_dir}")


if __name__ == "__main__":
    main()

