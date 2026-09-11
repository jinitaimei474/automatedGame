from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from PIL import Image

from check_dataset import check_dataset
from make_dataset_yaml import build_yaml, read_classes
from split_dataset import allocate, split_dataset


def create_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color=(20, 40, 60)).save(path)


def test_make_dataset_yaml_from_classes(tmp_path: Path) -> None:
    classes = tmp_path / "classes.txt"
    classes.write_text("person\ncar\n", encoding="utf-8")
    output = tmp_path / "dataset.yaml"
    content = build_yaml(classes, output)
    assert content["names"] == {0: "person", 1: "car"}
    assert yaml.safe_load(output.read_text(encoding="utf-8"))["train"] == "images/train"


def test_duplicate_classes_are_rejected(tmp_path: Path) -> None:
    classes = tmp_path / "classes.txt"
    classes.write_text("person\nperson\n", encoding="utf-8")
    with pytest.raises(ValueError, match="重复"):
        read_classes(classes)


def test_allocate_keeps_all_samples() -> None:
    assert allocate(11, 0.8, 0.1) == (8, 1, 2)


def test_split_and_check_valid_dataset(tmp_path: Path) -> None:
    raw_images = tmp_path / "raw/images"
    raw_labels = tmp_path / "raw/labels"
    for index in range(10):
        create_image(raw_images / f"sample-{index}.jpg")
        raw_labels.mkdir(parents=True, exist_ok=True)
        (raw_labels / f"sample-{index}.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
    dataset = tmp_path / "datasets"
    counts = split_dataset(raw_images, raw_labels, dataset, (0.8, 0.1, 0.1), seed=7)
    assert counts == {"train": 8, "val": 1, "test": 1}
    data_file = tmp_path / "dataset.yaml"
    data_file.write_text("path: datasets\ntrain: images/train\nval: images/val\ntest: images/test\nnames: [object]\n", encoding="utf-8")
    report, names = check_dataset(data_file)
    assert names == ["object"]
    assert not report.errors
    assert report.images == {"train": 8, "val": 1, "test": 1}


def test_invalid_box_is_reported(tmp_path: Path) -> None:
    for split in ("train", "val", "test"):
        image = tmp_path / f"datasets/images/{split}/item-{split}.jpg"
        create_image(image)
        label = tmp_path / f"datasets/labels/{split}/item-{split}.txt"
        label.parent.mkdir(parents=True, exist_ok=True)
        label.write_text("2 0.9 0.5 0.5 0.5\n", encoding="utf-8")
    data_file = tmp_path / "dataset.yaml"
    data_file.write_text("path: datasets\ntrain: images/train\nval: images/val\ntest: images/test\nnames: [object]\n", encoding="utf-8")
    report, _ = check_dataset(data_file, verify_images=False)
    assert any("类别 ID 越界" in error for error in report.errors)
    assert any("边界框超出图像" in error for error in report.errors)

