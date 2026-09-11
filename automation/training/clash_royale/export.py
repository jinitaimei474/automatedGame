from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 ONNX 模型")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--dynamic", action="store_true")
    args = parser.parse_args()
    from ultralytics import YOLO
    output = YOLO(args.weights).export(format="onnx", imgsz=args.imgsz, opset=args.opset, dynamic=args.dynamic)
    print(output)


if __name__ == "__main__":
    main()

