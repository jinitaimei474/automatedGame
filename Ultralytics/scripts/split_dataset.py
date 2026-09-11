from __future__ import annotations

import argparse
import random
import shutil
from collections import Counter
from pathlib import Path

from common import IMAGE_SUFFIXES, ROOT, resolve_from_root


def allocate(total: int, train: float, val: float) -> tuple[int, int, int]:
    train_count = int(total * train)
    val_count = int(total * val)
    return train_count, val_count, total - train_count - val_count


def clear_split_directories(output: Path) -> None:
    resolved = output.resolve()
    if resolved == resolved.anchor or len(resolved.parts) < 3:
        raise ValueError(f"拒绝清空过宽路径: {resolved}")
    for kind in ("images", "labels"):
        for split in ("train", "val", "test"):
            target = resolved / kind / split
            if target.is_dir():
                for item in target.iterdir():
                    if item.name != ".gitkeep":
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()


def split_dataset(raw_images: Path, raw_labels: Path, output: Path, ratios: tuple[float, float, float], seed: int,
                  move: bool = False, clear: bool = False, allow_unlabeled: bool = False) -> dict[str, int]:
    if any(value < 0 for value in ratios) or abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("train/val/test 比例必须为非负数且总和等于 1")
    images = sorted(path for path in raw_images.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError(f"原始图片目录为空: {raw_images}")
    pairs: list[tuple[Path, Path | None]] = []
    seen_stems: Counter[str] = Counter(image.stem.lower() for image in images)
    duplicates = [stem for stem, count in seen_stems.items() if count > 1]
    if duplicates:
        raise ValueError(f"原始图片存在重复文件名，无法安全匹配标签: {duplicates[:10]}")
    for image in images:
        label = raw_labels / f"{image.stem}.txt"
        if not label.is_file() and not allow_unlabeled:
            raise FileNotFoundError(f"图片缺少标签: {image} -> {label}")
        pairs.append((image, label if label.is_file() else None))
    random.Random(seed).shuffle(pairs)
    train_count, val_count, _ = allocate(len(pairs), ratios[0], ratios[1])
    groups = {
        "train": pairs[:train_count],
        "val": pairs[train_count:train_count + val_count],
        "test": pairs[train_count + val_count:],
    }
    if clear:
        clear_split_directories(output)
    operation = shutil.move if move else shutil.copy2
    for split, samples in groups.items():
        image_target = output / "images" / split
        label_target = output / "labels" / split
        image_target.mkdir(parents=True, exist_ok=True)
        label_target.mkdir(parents=True, exist_ok=True)
        for image, label in samples:
            operation(str(image), str(image_target / image.name))
            target_label = label_target / f"{image.stem}.txt"
            if label:
                operation(str(label), str(target_label))
            else:
                target_label.write_text("", encoding="utf-8")
    return {split: len(samples) for split, samples in groups.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="将 raw 图片和 YOLO 标签确定性划分为 train/val/test")
    parser.add_argument("--images", default=str(ROOT / "datasets/raw/images"))
    parser.add_argument("--labels", default=str(ROOT / "datasets/raw/labels"))
    parser.add_argument("--output", default=str(ROOT / "datasets"))
    parser.add_argument("--train", type=float, default=0.8)
    parser.add_argument("--val", type=float, default=0.1)
    parser.add_argument("--test", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--move", action="store_true", help="移动而不是复制原始文件")
    parser.add_argument("--clear", action="store_true", help="先清空已有划分（保留 .gitkeep）")
    parser.add_argument("--allow-unlabeled", action="store_true", help="将无标签图片作为空标签负样本")
    args = parser.parse_args()
    result = split_dataset(resolve_from_root(args.images), resolve_from_root(args.labels), resolve_from_root(args.output),
                           (args.train, args.val, args.test), args.seed, args.move, args.clear, args.allow_unlabeled)
    print(f"划分完成: train={result['train']}, val={result['val']}, test={result['test']}")


if __name__ == "__main__":
    main()

