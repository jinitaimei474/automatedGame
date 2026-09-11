from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


COLORS = [
    "#22c55e",
    "#3b82f6",
    "#f59e0b",
    "#ef4444",
    "#a855f7",
    "#06b6d4",
    "#ec4899",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render YOLO prelabel previews for human QA")
    parser.add_argument("images", type=Path, help="Prelabel images directory")
    parser.add_argument("labels", type=Path, help="Prelabel labels directory")
    parser.add_argument("classes", type=Path, help="classes.txt")
    parser.add_argument("output", type=Path, help="Preview output directory")
    parser.add_argument("names", nargs="+", help="Image filenames to render")
    args = parser.parse_args()

    class_names = args.classes.read_text(encoding="utf-8").splitlines()
    args.output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=24)

    for name in args.names:
        image_path = args.images / name
        label_path = args.labels / f"{image_path.stem}.txt"
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for line in label_path.read_text(encoding="utf-8").splitlines():
            class_id_text, cx_text, cy_text, bw_text, bh_text = line.split()
            class_id = int(class_id_text)
            cx, cy, bw, bh = map(float, (cx_text, cy_text, bw_text, bh_text))
            x1 = round((cx - bw / 2) * width)
            y1 = round((cy - bh / 2) * height)
            x2 = round((cx + bw / 2) * width)
            y2 = round((cy + bh / 2) * height)
            color = COLORS[class_id % len(COLORS)]
            line_width = max(3, round(min(width, height) / 300))
            draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
            label = class_names[class_id]
            left, top, right, bottom = draw.textbbox((x1, y1), label, font=font)
            draw.rectangle((left - 2, top - 2, right + 4, bottom + 4), fill=color)
            draw.text((x1 + 1, y1 + 1), label, fill="white", font=font)
        image.thumbnail((720, 1280), Image.Resampling.LANCZOS)
        image.save(args.output / f"{image_path.stem}_preview.jpg", quality=92)


if __name__ == "__main__":
    main()
