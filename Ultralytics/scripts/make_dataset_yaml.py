from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from common import ROOT, resolve_from_root


def read_classes(path: Path) -> list[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not names:
        raise ValueError("classes.txt 至少需要一个类别")
    if len(set(names)) != len(names):
        raise ValueError("classes.txt 中存在重复类别")
    return names


def build_yaml(classes_file: Path, output: Path, dataset_path: str = "datasets") -> dict[str, object]:
    names = read_classes(classes_file)
    content: dict[str, object] = {
        "path": dataset_path,
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(names)},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="根据 classes.txt 生成通用 YOLO dataset.yaml")
    parser.add_argument("--classes", default=str(ROOT / "classes.txt"), help="每行一个类别名称")
    parser.add_argument("--output", default=str(ROOT / "dataset.yaml"))
    parser.add_argument("--dataset-path", default="datasets", help="写入 YAML 的数据集根目录")
    args = parser.parse_args()
    content = build_yaml(resolve_from_root(args.classes), resolve_from_root(args.output), args.dataset_path)
    print(f"已生成 {resolve_from_root(args.output)}，共 {len(content['names'])} 个类别")


if __name__ == "__main__":
    main()

