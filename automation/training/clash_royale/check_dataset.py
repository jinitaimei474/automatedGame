from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASS_COUNT = 34


def check_split(dataset: Path, split: str) -> tuple[list[str], Counter[int]]:
    errors: list[str] = []
    counts: Counter[int] = Counter()
    image_dir = dataset / "images" / split
    label_dir = dataset / "labels" / split
    for image in image_dir.iterdir():
        if image.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        label = label_dir / f"{image.stem}.txt"
        if not label.exists():
            errors.append(f"缺少标签: {label}")
            continue
        for line_number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), start=1):
            parts = line.split()
            if len(parts) != 5:
                errors.append(f"{label}:{line_number} 应为 5 列")
                continue
            try:
                class_id = int(parts[0]); coords = [float(value) for value in parts[1:]]
                if not 0 <= class_id < CLASS_COUNT or any(not 0 <= value <= 1 for value in coords):
                    raise ValueError
                counts[class_id] += 1
            except ValueError:
                errors.append(f"{label}:{line_number} 类别或坐标无效")
    return errors, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 YOLO 数据集标签配对和格式")
    parser.add_argument("--dataset", default=str(Path(__file__).parent / "datasets"))
    args = parser.parse_args(); root = Path(args.dataset)
    all_errors: list[str] = []; total: Counter[int] = Counter()
    for split in ("train", "val", "test"):
        errors, counts = check_split(root, split); all_errors.extend(errors); total.update(counts)
        print(f"{split}: {sum(counts.values())} 个标注")
    if all_errors:
        print("\n".join(all_errors)); raise SystemExit(1)
    print(f"数据集格式检查通过，类别分布: {dict(sorted(total.items()))}")


if __name__ == "__main__":
    main()

