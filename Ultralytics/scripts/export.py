from __future__ import annotations

import argparse

from common import import_yolo, resolve_from_root


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 YOLO 检测模型")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--format", choices=("onnx", "openvino", "engine", "torchscript", "coreml", "tflite", "saved_model", "ncnn"), default="onnx")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--opset", type=int, default=None)
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--simplify", action="store_true")
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--workspace", type=float, default=4.0, help="TensorRT 工作区 GiB")
    args = parser.parse_args()
    if args.half and args.int8:
        raise SystemExit("--half 与 --int8 不能同时使用")
    if args.format == "engine" and args.device == "cpu":
        raise SystemExit("TensorRT engine 导出需要 NVIDIA GPU，例如 --device 0")
    YOLO = import_yolo()
    output = YOLO(str(resolve_from_root(args.weights))).export(
        format=args.format, imgsz=args.imgsz, device=args.device, opset=args.opset, dynamic=args.dynamic,
        simplify=args.simplify, half=args.half, int8=args.int8, batch=args.batch, workspace=args.workspace,
    )
    print(f"导出完成: {output}")


if __name__ == "__main__":
    main()

