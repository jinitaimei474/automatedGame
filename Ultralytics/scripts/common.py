from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / ".runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
ULTRALYTICS_CONFIG_DIR = RUNTIME_DIR / "ultralytics"
MATPLOTLIB_CONFIG_DIR = RUNTIME_DIR / "matplotlib"
ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MATPLOTLIB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CONFIG_DIR))

IMAGE_SUFFIXES = {".bmp", ".dng", ".jpeg", ".jpg", ".mpo", ".png", ".tif", ".tiff", ".webp"}


def add_root_to_path() -> None:
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def resolve_from_root(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    from_cwd = (Path.cwd() / path).resolve()
    return from_cwd if from_cwd.exists() else (ROOT / path).resolve()


def load_yaml(path: str | Path) -> dict[str, Any]:
    import yaml

    target = resolve_from_root(path)
    content = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError(f"YAML 根节点必须是对象: {target}")
    return content


def class_names(data: dict[str, Any]) -> list[str]:
    names = data.get("names")
    if isinstance(names, list):
        result = [str(item).strip() for item in names]
    elif isinstance(names, dict):
        try:
            ordered = sorted((int(key), str(value).strip()) for key, value in names.items())
        except (TypeError, ValueError) as exc:
            raise ValueError("names 字典的键必须是连续整数") from exc
        if [key for key, _ in ordered] != list(range(len(ordered))):
            raise ValueError("names 类别 ID 必须从 0 开始连续排列")
        result = [value for _, value in ordered]
    else:
        raise ValueError("dataset.yaml 必须包含 names 列表或字典")
    if not result or any(not name for name in result):
        raise ValueError("类别名称不能为空")
    if len(set(result)) != len(result):
        raise ValueError("类别名称不能重复")
    return result


def dataset_root(data_file: str | Path, data: dict[str, Any]) -> Path:
    configured = Path(str(data.get("path", "datasets"))).expanduser()
    if configured.is_absolute():
        return configured.resolve()
    data_path = resolve_from_root(data_file)
    candidate = (data_path.parent / configured).resolve()
    return candidate


def import_yolo():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("未安装 ultralytics。请先运行 powershell -File tools/setup.ps1") from exc
    return YOLO
