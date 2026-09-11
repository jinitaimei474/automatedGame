from __future__ import annotations

import argparse
import statistics
import time

from common import import_yolo, resolve_from_root


def main() -> None:
    parser = argparse.ArgumentParser(description="测量模型单张推理延迟和吞吐量")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--source", required=True, help="一张测试图片")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()
    if args.warmup < 0 or args.runs < 1:
        raise SystemExit("warmup 不能为负数，runs 至少为 1")
    YOLO = import_yolo()
    model = YOLO(str(resolve_from_root(args.weights)))
    source = str(resolve_from_root(args.source))
    for _ in range(args.warmup):
        model.predict(source, imgsz=args.imgsz, device=args.device, verbose=False)
    timings: list[float] = []
    for _ in range(args.runs):
        started = time.perf_counter()
        model.predict(source, imgsz=args.imgsz, device=args.device, verbose=False)
        timings.append((time.perf_counter() - started) * 1000)
    mean = statistics.mean(timings)
    sorted_times = sorted(timings)
    p95 = sorted_times[min(len(sorted_times) - 1, round(len(sorted_times) * 0.95) - 1)]
    print(f"平均延迟: {mean:.2f} ms")
    print(f"P95 延迟: {p95:.2f} ms")
    print(f"吞吐量: {1000 / mean:.2f} FPS")


if __name__ == "__main__":
    main()

