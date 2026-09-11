from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import cv2
import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate reviewable YOLO prelabels for the Clash Royale image corpus")
    parser.add_argument("--raw", type=Path, default=base / "datasets" / "raw")
    parser.add_argument("--classes", type=Path, default=base / "dataset.yaml")
    parser.add_argument("--output", type=Path, default=base / "datasets" / "prelabels_gpt56sol")
    parser.add_argument("--force", action="store_true", help="Allow overwriting generated files in an existing output directory")
    return parser.parse_args()


def load_classes(path: Path) -> tuple[dict[int, str], dict[str, int]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    id_to_name = {int(key): str(value) for key, value in data["names"].items()}
    return id_to_name, {name: class_id for class_id, name in id_to_name.items()}


def xyxy_to_yolo(box: tuple[int, int, int, int], width: int, height: int) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    return (
        ((x1 + x2) / 2) / width,
        ((y1 + y2) / 2) / height,
        (x2 - x1) / width,
        (y2 - y1) / height,
    )


def clipped_box(box: tuple[float, float, float, float], width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    x1 = max(0, min(width - 2, round(x1)))
    y1 = max(0, min(height - 2, round(y1)))
    x2 = max(x1 + 1, min(width - 1, round(x2)))
    y2 = max(y1 + 1, min(height - 1, round(y2)))
    return x1, y1, x2, y2


def full_frame(width: int, height: int) -> tuple[int, int, int, int]:
    return 1, 1, width - 1, height - 1


def add_annotation(
    annotations: list[dict[str, object]],
    class_name: str,
    box: tuple[int, int, int, int],
    confidence: float,
    provenance: str,
    rationale: str,
    width: int,
    height: int,
    name_to_id: dict[str, int],
) -> None:
    yolo = xyxy_to_yolo(box, width, height)
    annotations.append(
        {
            "class_id": name_to_id[class_name],
            "label": class_name,
            "confidence": round(confidence, 3),
            "bbox_xyxy": list(box),
            "bbox_yolo": [round(value, 6) for value in yolo],
            "provenance": provenance,
            "rationale": rationale,
            "review_status": "must_review",
        }
    )


def template_box(image: cv2.typing.MatLike, template: cv2.typing.MatLike, threshold: float) -> tuple[tuple[int, int, int, int] | None, float]:
    target_width = 540
    scale = target_width / image.shape[1]
    resized = cv2.resize(image, (target_width, round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    template_resized = cv2.resize(
        template,
        (round(template.shape[1] * scale), round(template.shape[0] * scale)),
        interpolation=cv2.INTER_AREA,
    )
    image_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_resized, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    if score < threshold:
        return None, float(score)
    x1 = round(location[0] / scale)
    y1 = round(location[1] / scale)
    x2 = x1 + template.shape[1]
    y2 = y1 + template.shape[0]
    return (x1, y1, x2, y2), float(score)


def prepare_templates(raw: Path) -> dict[str, cv2.typing.MatLike]:
    templates: dict[str, cv2.typing.MatLike] = {}
    shop = cv2.imread(str(raw / "supplement_50_each" / "shop_daily_selection" / "shop_daily_025.png"))
    if shop is not None:
        height, width = shop.shape[:2]
        templates["daily_header"] = shop[round(height * 0.272) : round(height * 0.326), round(width * 0.055) : round(width * 0.945)]
        templates["free_item"] = shop[round(height * 0.355) : round(height * 0.705), round(width * 0.012) : round(width * 0.321)]
    mode = cv2.imread(str(raw / "supplement_50_each" / "game_mode_selection" / "game_mode_001.png"))
    if mode is not None:
        height, width = mode.shape[:2]
        templates["classic_1v1"] = mode[round(height * 0.565) : round(height * 0.706), round(width * 0.018) : round(width * 0.982)]
    return templates


def annotate_curated(
    row: dict[str, str],
    image_path: Path,
    width: int,
    height: int,
    annotations: list[dict[str, object]],
    candidates: list[dict[str, object]],
    name_to_id: dict[str, int],
) -> tuple[str, str]:
    suggested = row.get("suggested_labels", "")
    filename = image_path.name.lower()
    source_id = row.get("source_id", "")
    match = re.search(r"_(\d+)$", image_path.stem)
    frame_index = int(match.group(1)) if match else -1
    if suggested == "System.Object[]" and "game_mode" in filename:
        suggested = "game_mode_panel"

    if source_id == "BV1L2MX6cEsd":
        if frame_index == 53:
            add_annotation(annotations, "matching_screen", full_frame(width, height), 0.94, "sequence_visual_review", "画面明确显示搜索对手与取消按钮", width, height, name_to_id)
            candidates.append({"label": "cancel_matching", "reason": "需紧贴红色取消按钮补框"})
            return "medium", "补画取消匹配按钮并确认边界"
        if frame_index in {51, 83, 170, 171, 230, 257, 294, 295}:
            add_annotation(annotations, "battle_end", full_frame(width, height), 0.91, "sequence_visual_review", "逐帧检查确认处于对战结束或皇冠结算过渡", width, height, name_to_id)
            if frame_index in {51, 171}:
                add_annotation(annotations, "victory_screen", full_frame(width, height), 0.80, "sequence_outcome_review", "己方最终皇冠多于对方", width, height, name_to_id)
                candidates.append({"label": "result_crowns_1" if frame_index == 51 else "result_crowns_2", "reason": "仅在己方皇冠数稳定可见时保留"})
            elif frame_index == 295:
                add_annotation(annotations, "defeat_screen", full_frame(width, height), 0.80, "sequence_outcome_review", "己方最终皇冠少于对方", width, height, name_to_id)
                candidates.append({"label": "result_crowns_1", "reason": "仅在己方1冠稳定可见时保留"})
            else:
                candidates.extend(
                    [
                        {"label": "victory_screen", "reason": "按最终皇冠比较确认"},
                        {"label": "defeat_screen", "reason": "按最终皇冠比较确认"},
                    ]
                )
            return "high", "结算帧必须人工确认胜负与己方最终皇冠总数"
        if frame_index in {52, 84, 127, 128, 172, 231, 296, 305}:
            candidates.append({"label": "unsupported_non_battle_ui", "reason": "卡组页或加载页不属于当前34类中的场景类"})
            return "high", "确认无目标后保留空标签文件；不要误标 battle_screen"
        if 297 <= frame_index <= 304:
            candidates.append({"label": "close_button", "reason": "卡牌详情页右上角红色关闭按钮可紧框"})
            return "high", "卡牌详情本身无对应类别；仅补画明确可见的关闭按钮"
        if frame_index == 306:
            add_annotation(annotations, "shop_screen", full_frame(width, height), 0.93, "sequence_visual_review", "视频末段明确切换到金币商店页", width, height, name_to_id)
            candidates.append({"label": "currency_price", "reason": "逐个紧贴三个宝石价格补框"})
            return "medium", "补画可见价格，勿把金币数量当价格"
        if frame_index == 307:
            add_annotation(annotations, "shop_screen", full_frame(width, height), 0.86, "sequence_visual_review", "创作者代码弹窗后方仍为商店页", width, height, name_to_id)
            add_annotation(annotations, "unknown_blocking_popup", clipped_box((width * 0.12, height * 0.28, width * 0.88, height * 0.69), width, height), 0.72, "sequence_visual_review", "创作者代码弹窗遮挡主要商店操作区域", width, height, name_to_id)
            candidates.append({"label": "close_button", "reason": "弹窗右上角红色关闭按钮可紧框"})
            return "high", "确认是否将创作者弹窗纳入阻塞类，并补画关闭按钮"
        add_annotation(annotations, "battle_screen", full_frame(width, height), 0.82, "sequence_visual_review", "公开视频逐段检查后属于对局或VS开局画面", width, height, name_to_id)
        return "medium", "确认是否恰逢结算动画；VS对阵卡仍归 battle_screen"

    if source_id == "BV19UQuYQEQ2":
        if frame_index in {45, 46, 125, 126, 200, 201}:
            add_annotation(annotations, "battle_end", full_frame(width, height), 0.94, "sequence_visual_review", "已按视频时间线定位对战结束与结算板", width, height, name_to_id)
            if frame_index == 46:
                add_annotation(annotations, "defeat_screen", full_frame(width, height), 0.86, "sequence_outcome_review", "第一局结算己方1冠、对方2冠", width, height, name_to_id)
                candidates.append({"label": "result_crowns_1", "reason": "己方1冠完整结果区域需人工紧框"})
            elif frame_index == 126:
                add_annotation(annotations, "victory_screen", full_frame(width, height), 0.86, "sequence_outcome_review", "第二局结算己方1冠、对方0冠", width, height, name_to_id)
                candidates.append({"label": "result_crowns_1", "reason": "己方1冠完整结果区域需人工紧框"})
            elif frame_index == 201:
                add_annotation(annotations, "defeat_screen", full_frame(width, height), 0.84, "sequence_outcome_review", "第三局结算己方0冠、对方1冠", width, height, name_to_id)
                candidates.append({"label": "result_crowns_0", "reason": "己方0冠完整结果区域需人工紧框"})
            else:
                candidates.extend(
                    [
                        {"label": "victory_screen", "reason": "动画尚未稳定，按后续最终结果确认"},
                        {"label": "defeat_screen", "reason": "动画尚未稳定，按后续最终结果确认"},
                    ]
                )
            return "high", "逐帧确认胜负与己方皇冠数，未稳定时只保留 battle_end"
        if frame_index in {48, 127}:
            add_annotation(annotations, "matching_screen", full_frame(width, height), 0.97, "sequence_visual_review", "画面明确显示搜索对手与取消按钮", width, height, name_to_id)
            candidates.append({"label": "cancel_matching", "reason": "需紧贴红色取消按钮补框"})
            return "medium", "补画取消匹配按钮"
        if frame_index in {47, 202}:
            candidates.append({"label": "unsupported_loading_screen", "reason": "纯加载画面不属于当前34类"})
            return "high", "确认无目标后保留空标签文件"
        if frame_index == 203:
            add_annotation(annotations, "home_screen", full_frame(width, height), 0.91, "sequence_visual_review", "视频结尾已返回主页面", width, height, name_to_id)
            return "medium", "主页弹窗若不属于现有类别则不要硬标"
        add_annotation(annotations, "battle_screen", full_frame(width, height), 0.86, "sequence_visual_review", "按时间线排除结算、匹配和加载帧后的对局画面", width, height, name_to_id)
        return "medium", "确认竞技场仍在对局语境；VS过场也归 battle_screen"

    if "shop_screen" in suggested:
        add_annotation(annotations, "shop_screen", full_frame(width, height), 0.92, "manifest_plus_filename", "本机模拟器商店截图", width, height, name_to_id)
        if "currency_price" in suggested:
            candidates.append({"label": "currency_price", "reason": "需逐个紧贴可见价格文字绘框"})
        return "medium", "需补画每个实际可见的价格、免费物品和领取状态"

    if "home_screen" in suggested:
        add_annotation(annotations, "home_screen", full_frame(width, height), 0.96, "manifest_plus_filename", "本机模拟器主页截图", width, height, name_to_id)
        candidates.extend(
            [
                {"label": "battle_button", "reason": "需紧贴主页对战按钮"},
                {"label": "leftmost_nav_tab", "reason": "需紧贴最左侧底部导航按钮"},
            ]
        )
        return "medium", "场景可信，两个按钮框需人工补画"

    if "game_mode_panel" in suggested or "game_mode" in filename:
        add_annotation(annotations, "game_mode_panel", clipped_box((0, height * 0.12, width, height), width, height), 0.95, "manifest_plus_filename", "本机模拟器游戏模式面板", width, height, name_to_id)
        candidates.append({"label": "classic_1v1", "reason": "若经典1对1卡片完整可见则补框"})
        return "medium", "检查面板上缘并补画完整可见的经典1对1卡片"

    candidates.append({"label": "unknown", "reason": f"无法解析原建议字段：{suggested!r}"})
    return "high", "无可靠预标，必须人工从零标注"


def annotate_supplement(
    row: dict[str, str],
    image_path: Path,
    image: cv2.typing.MatLike,
    templates: dict[str, cv2.typing.MatLike],
    annotations: list[dict[str, object]],
    candidates: list[dict[str, object]],
    name_to_id: dict[str, int],
) -> tuple[str, str]:
    height, width = image.shape[:2]
    category = row["category"]
    subtype = row["subtype"]

    if category == "shop_daily_selection":
        add_annotation(annotations, "shop_screen", full_frame(width, height), 0.99, "collection_category", "本机模拟器商店采集目录", width, height, name_to_id)
        header_box, header_score = template_box(image, templates["daily_header"], 0.53)
        if header_box:
            add_annotation(annotations, "daily_trader", clipped_box(header_box, width, height), min(0.96, header_score), "template_match", "匹配每日精选标题条", width, height, name_to_id)
        else:
            candidates.append({"label": "daily_trader", "reason": f"标题可能滚出画面，模板分数 {header_score:.3f}"})
        item_box, item_score = template_box(image, templates["free_item"], 0.52)
        if item_box:
            item_box = clipped_box(item_box, width, height)
            add_annotation(annotations, "free_item", item_box, min(0.90, item_score), "template_match", "匹配每日精选左侧免费金币商品卡", width, height, name_to_id)
            x1, y1, x2, y2 = item_box
            claimed = clipped_box((x1 + (x2 - x1) * 0.18, y1 + (y2 - y1) * 0.68, x2 - (x2 - x1) * 0.12, y2 - (y2 - y1) * 0.02), width, height)
            add_annotation(annotations, "claimed_state", claimed, 0.72, "relative_to_template", "免费商品卡内的绿色勾与已收集状态候选", width, height, name_to_id)
        else:
            candidates.append({"label": "free_item", "reason": f"商品卡可能被滚动裁切，模板分数 {item_score:.3f}"})
        candidates.append({"label": "currency_price", "reason": "逐个框选当前画面中完整可见的金币/宝石价格"})
        return "medium", "核对每日精选标题和商品卡边界；补齐全部可见价格"

    if category == "game_mode_selection":
        panel = clipped_box((0, height * 0.12, width, height), width, height)
        add_annotation(annotations, "game_mode_panel", panel, 0.99, "collection_category", "本机模拟器游戏模式选择页", width, height, name_to_id)
        classic_box, score = template_box(image, templates["classic_1v1"], 0.90)
        if classic_box:
            add_annotation(annotations, "classic_1v1", clipped_box(classic_box, width, height), min(0.96, score), "template_match", "匹配完整的经典1对1模式卡", width, height, name_to_id)
            return "medium", "检查经典1对1卡片是否完整可见并收紧边界"
        candidates.append({"label": "classic_1v1", "reason": f"卡片可能被标题栏遮挡或滚出画面，模板分数 {score:.3f}"})
        return "medium", "经典1对1不完整时不要强标；完整可见时人工补框"

    if category == "battle_start_end" and subtype == "battle_start_transition":
        add_annotation(annotations, "battle_screen", full_frame(width, height), 0.92, "collection_subtype", "VS过场、空场或开战提示均已进入对局语境", width, height, name_to_id)
        candidates.append({"label": "matching_screen", "reason": "仅当仍是搜寻对手/取消匹配界面时替换；VS过场不算 matching_screen"})
        return "medium", "确认是否已进入竞技场；错误的 matching_screen 候选不要添加"

    if category == "battle_start_end" and subtype == "battle_end_result":
        add_annotation(annotations, "battle_end", full_frame(width, height), 0.98, "collection_subtype", "对战结束或皇冠结算过渡", width, height, name_to_id)
        match = re.search(r"(\d+)$", image_path.stem)
        index = int(match.group(1)) if match else -1
        if 34 <= index <= 38:
            add_annotation(annotations, "defeat_screen", full_frame(width, height), 0.82, "sequence_outcome_review", "第一段结算中己方皇冠少于对方", width, height, name_to_id)
            candidates.append({"label": "result_crowns_1", "reason": "只有己方1冠结果已经稳定显示时才保留"})
        elif 43 <= index <= 50:
            add_annotation(annotations, "victory_screen", full_frame(width, height), 0.82, "sequence_outcome_review", "第二段结算中己方皇冠多于对方", width, height, name_to_id)
            candidates.append({"label": "result_crowns_1", "reason": "只有己方1冠结果已经稳定显示时才保留"})
        else:
            candidates.extend(
                [
                    {"label": "victory_screen", "reason": "结算动画尚未稳定，按最终皇冠比较确认"},
                    {"label": "defeat_screen", "reason": "结算动画尚未稳定，按最终皇冠比较确认"},
                ]
            )
        return "high", "胜负和己方皇冠数必须以稳定后的结算板为准"

    candidates.append({"label": "unknown", "reason": f"未处理目录组合 {category}/{subtype}"})
    return "high", "无可靠预标，必须人工从零标注"


def hardlink_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return "existing"
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Output is not empty: {output}. Re-run with --force to overwrite generated files.")
    images_out = output / "images"
    labels_out = output / "labels"
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    id_to_name, name_to_id = load_classes(args.classes)
    templates = prepare_templates(args.raw)
    if set(templates) != {"daily_header", "free_item", "classic_1v1"}:
        raise SystemExit(f"Missing templates: {sorted({'daily_header', 'free_item', 'classic_1v1'} - set(templates))}")

    sources: list[tuple[str, dict[str, str], Path, str]] = []
    curated_root = args.raw / "curated"
    with (curated_root / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            path = curated_root / row["file"]
            sources.append(("curated", row, path, f"curated__{path.name}"))

    supplement_root = args.raw / "supplement_50_each"
    with (supplement_root / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            path = supplement_root / row["relative_path"]
            category = row["category"]
            sources.append(("supplement", row, path, f"supplement__{category}__{path.name}"))

    annotations_path = output / "annotations.jsonl"
    review_path = output / "review_queue.csv"
    map_path = output / "image_map.csv"
    summary_counts: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    link_counts: Counter[str] = Counter()
    annotated_images = 0
    candidate_only_images = 0
    errors: list[str] = []

    with annotations_path.open("w", encoding="utf-8", newline="") as jsonl, review_path.open("w", encoding="utf-8-sig", newline="") as review_handle, map_path.open("w", encoding="utf-8-sig", newline="") as map_handle:
        review_writer = csv.DictWriter(
            review_handle,
            fieldnames=["review_image", "source_image", "session_group", "priority", "prelabels", "candidate_labels", "review_reason", "review_status", "reviewer", "review_notes"],
        )
        review_writer.writeheader()
        map_writer = csv.DictWriter(map_handle, fieldnames=["review_image", "review_label", "source_image", "link_mode"])
        map_writer.writeheader()

        for source_kind, row, image_path, review_name in sources:
            image = cv2.imread(str(image_path))
            if image is None:
                errors.append(str(image_path))
                continue
            height, width = image.shape[:2]
            annotations: list[dict[str, object]] = []
            candidates: list[dict[str, object]] = []
            if source_kind == "curated":
                priority, reason = annotate_curated(row, image_path, width, height, annotations, candidates, name_to_id)
                session_group = row.get("source_id", "")
            else:
                priority, reason = annotate_supplement(row, image_path, image, templates, annotations, candidates, name_to_id)
                session_group = row.get("session_group", "")

            destination = images_out / review_name
            link_mode = hardlink_or_copy(image_path, destination)
            link_counts[link_mode] += 1
            label_path = labels_out / f"{Path(review_name).stem}.txt"
            lines = []
            if annotations:
                annotated_images += 1
            elif candidates:
                candidate_only_images += 1
            for annotation in annotations:
                summary_counts[str(annotation["label"])] += 1
                values = annotation["bbox_yolo"]
                lines.append(f"{annotation['class_id']} " + " ".join(f"{float(value):.6f}" for value in values))
            for candidate in candidates:
                candidate_counts[str(candidate["label"])] += 1
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

            priority_counts[priority] += 1
            record = {
                "review_image": f"images/{review_name}",
                "review_label": f"labels/{label_path.name}",
                "source_image": str(image_path.resolve()),
                "source_kind": source_kind,
                "width": width,
                "height": height,
                "session_group": session_group,
                "annotations": annotations,
                "candidate_labels": candidates,
                "priority": priority,
                "review_reason": reason,
                "review_status": "pending",
            }
            jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")
            review_writer.writerow(
                {
                    "review_image": record["review_image"],
                    "source_image": record["source_image"],
                    "session_group": session_group,
                    "priority": priority,
                    "prelabels": ",".join(str(item["label"]) for item in annotations),
                    "candidate_labels": ",".join(str(item["label"]) for item in candidates),
                    "review_reason": reason,
                    "review_status": "pending",
                    "reviewer": "",
                    "review_notes": "",
                }
            )
            map_writer.writerow(
                {
                    "review_image": record["review_image"],
                    "review_label": record["review_label"],
                    "source_image": record["source_image"],
                    "link_mode": link_mode,
                }
            )

    (output / "classes.txt").write_text("\n".join(id_to_name[index] for index in sorted(id_to_name)) + "\n", encoding="utf-8")
    review_yaml = {
        "path": ".",
        "train": "images",
        "val": "images",
        "names": id_to_name,
    }
    (output / "dataset_review.yaml").write_text(yaml.safe_dump(review_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8")
    summary = {
        "images": sum(priority_counts.values()),
        "annotated_images": annotated_images,
        "candidate_only_images": candidate_only_images,
        "yolo_boxes": sum(summary_counts.values()),
        "class_counts": dict(sorted(summary_counts.items(), key=lambda item: name_to_id[item[0]])),
        "candidate_counts": dict(sorted(candidate_counts.items())),
        "review_priority_counts": dict(priority_counts),
        "image_link_modes": dict(link_counts),
        "unreadable_images": errors,
        "important": "These are prelabels, not ground truth. Every image remains pending human review.",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
