from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image

from common import IMAGE_SUFFIXES, ROOT, class_names, dataset_root, load_yaml, resolve_from_root


@dataclass
class DatasetReport:
    images: dict[str, int] = field(default_factory=dict)
    annotations: dict[str, int] = field(default_factory=dict)
    class_counts: Counter[int] = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_label(label: Path, class_count: int, report: DatasetReport) -> None:
    lines = label.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        report.warnings.append(f"空标签文件（负样本）: {label}")
    seen: set[str] = set()
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if line in seen:
            report.warnings.append(f"重复标注: {label}:{line_number}")
        seen.add(line)
        fields = line.split()
        if len(fields) != 5:
            report.errors.append(f"标签应为 5 列: {label}:{line_number}")
            continue
        try:
            class_id = int(fields[0])
            x, y, width, height = (float(value) for value in fields[1:])
        except ValueError:
            report.errors.append(f"标签包含非数字: {label}:{line_number}")
            continue
        if not 0 <= class_id < class_count:
            report.errors.append(f"类别 ID 越界: {label}:{line_number} -> {class_id}")
        if not all(0 <= value <= 1 for value in (x, y, width, height)):
            report.errors.append(f"归一化坐标必须位于 0～1: {label}:{line_number}")
        if width <= 0 or height <= 0:
            report.errors.append(f"宽高必须大于 0: {label}:{line_number}")
        if x - width / 2 < -1e-6 or x + width / 2 > 1 + 1e-6 or y - height / 2 < -1e-6 or y + height / 2 > 1 + 1e-6:
            report.errors.append(f"边界框超出图像: {label}:{line_number}")
        report.class_counts[class_id] += 1


def check_dataset(data_file: Path, verify_images: bool = True) -> tuple[DatasetReport, list[str]]:
    data = load_yaml(data_file)
    names = class_names(data)
    root = dataset_root(data_file, data)
    report = DatasetReport()
    stems_by_split: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        relative_images = data.get(split)
        if not relative_images:
            report.warnings.append(f"dataset.yaml 未配置 {split}")
            continue
        image_dir = root / str(relative_images)
        label_dir = root / "labels" / split
        if not image_dir.is_dir():
            report.errors.append(f"图片目录不存在: {image_dir}")
            continue
        if not label_dir.is_dir():
            report.errors.append(f"标签目录不存在: {label_dir}")
            continue
        images = sorted(path for path in image_dir.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
        report.images[split] = len(images)
        report.annotations[split] = 0
        stems_by_split[split] = {path.stem.lower() for path in images}
        image_stems = stems_by_split[split]
        for image in images:
            if verify_images:
                try:
                    with Image.open(image) as opened:
                        opened.verify()
                except Exception as exc:
                    report.errors.append(f"图片损坏: {image} ({exc})")
            label = label_dir / image.relative_to(image_dir).with_suffix(".txt")
            if not label.is_file():
                report.errors.append(f"缺少同名标签: {label}")
                continue
            parse_label(label, len(names), report)
            report.annotations[split] += sum(1 for line in label.read_text(encoding="utf-8-sig").splitlines() if line.strip())
        for label in label_dir.rglob("*.txt"):
            if label.stem.lower() not in image_stems:
                report.warnings.append(f"孤立标签（无同名图片）: {label}")
    split_names = list(stems_by_split)
    for index, first in enumerate(split_names):
        for second in split_names[index + 1:]:
            overlap = stems_by_split[first] & stems_by_split[second]
            if overlap:
                report.errors.append(f"{first}/{second} 存在 {len(overlap)} 个同名样本，疑似数据泄漏: {sorted(overlap)[:5]}")
    if report.images.get("train", 0) == 0:
        report.warnings.append("训练集为空")
    if report.images.get("val", 0) == 0:
        report.warnings.append("验证集为空")
    return report, names


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 YOLO 检测数据集配对、标签、图片和数据泄漏")
    parser.add_argument("--data", default=str(ROOT / "dataset.yaml"))
    parser.add_argument("--skip-image-verify", action="store_true")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--strict", action="store_true", help="警告也视为失败")
    args = parser.parse_args()
    report, names = check_dataset(resolve_from_root(args.data), not args.skip_image_verify)
    if args.json:
        payload = asdict(report); payload["class_counts"] = dict(report.class_counts); payload["classes"] = names
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"类别 ({len(names)}): {', '.join(names)}")
        for split in ("train", "val", "test"):
            print(f"{split}: {report.images.get(split, 0)} 张图片，{report.annotations.get(split, 0)} 个框")
        print("类别分布: " + ", ".join(f"{names[class_id] if 0 <= class_id < len(names) else class_id}={count}" for class_id, count in sorted(report.class_counts.items())))
        for warning in report.warnings:
            print(f"[警告] {warning}")
        for error in report.errors:
            print(f"[错误] {error}")
    if report.errors or (args.strict and report.warnings):
        raise SystemExit(1)
    print("数据集检查通过")


if __name__ == "__main__":
    main()

