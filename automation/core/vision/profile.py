"""Small, local screenshot recognizer. No trained weights or remote services."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .engine import Detection, VisionEngine


def roi_pixels(roi, width, height):
    if len(roi) != 4 or not (0 <= roi[0] < roi[2] <= 1 and 0 <= roi[1] < roi[3] <= 1):
        raise ValueError(f'无效归一化区域: {roi}')
    box = tuple(round(v * (width if i % 2 == 0 else height)) for i, v in enumerate(roi))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('区域小于一个像素')
    return box


class ProfileDetector:
    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.is_file():
            raise ValueError(f'模板配置不存在: {path}；请按 docs/RULE_BATTLE.zh-CN.md 创建并校准')
        self.profile = json.loads(path.read_text(encoding='utf-8'))
        coverage = self.profile.get('elixir_coverage', .6)
        if not isinstance(coverage, (int, float)) or not 0 < coverage <= 1:
            raise ValueError('elixir_coverage 必须在 (0, 1]')
        hsv = self.profile.get('elixir_hsv', [[125, 80, 80], [175, 255, 255]])
        if (len(hsv) != 2 or any(len(row) != 3 for row in hsv) or
            any(not 0 <= hsv[0][i] <= hsv[1][i] <= limit for i, limit in enumerate((179, 255, 255)))):
            raise ValueError('elixir_hsv 必须是 OpenCV HSV 有效上下界')
        self.width, self.height = self.profile['resolution']
        if min(self.width, self.height) < 1:
            raise ValueError('无效参考分辨率')
        entries = list(self.profile.get('templates', []))
        for card in self.profile.get('deck', []):
            for slot, roi in enumerate(self.profile.get('hand_rois', [])):
                if roi is None:
                    continue
                for filename in [card['file'], *card.get('variants', [])]:
                    entries.append({'label': f"card_{slot}_{card['name']}", 'file': filename,
                                    'roi': roi, 'threshold': card.get('threshold', .90)})
        self.templates = []
        for entry in entries:
            source = path.parent / entry['file']
            template = cv2.imdecode(np.frombuffer(source.read_bytes(), np.uint8), cv2.IMREAD_COLOR) if source.is_file() else None
            if template is None or template.size == 0 or template.std() < 1:
                raise ValueError(f'模板缺失、空白或不可读: {source}')
            box = roi_pixels(entry['roi'], self.width, self.height)
            if 'target' in entry:
                roi_pixels(entry['target'], self.width, self.height)
            if template.shape[1] > box[2]-box[0] or template.shape[0] > box[3]-box[1]:
                raise ValueError(f'模板大于搜索区域: {source}')
            threshold = entry.get('threshold', .90)
            if not 0 < threshold <= 1:
                raise ValueError('模板阈值须在 (0, 1]')
            self.templates.append((entry, template, box))
        for roi in self.profile.get('elixir_rois', []):
            if roi is not None:
                roi_pixels(roi, self.width, self.height)
        self.crown_slots = []
        for slot in self.profile.get('crown_slots', []):
            box = roi_pixels(slot['roi'], self.width, self.height)
            empty = cv2.imdecode(np.frombuffer((path.parent / slot['empty_file']).read_bytes(), np.uint8), 1)
            if empty is None or empty.shape[:2] != (box[3]-box[1], box[2]-box[0]):
                raise ValueError('皇冠空槽模板尺寸必须和区域一致')
            if not 0 < slot.get('active_coverage', .25) <= 1:
                raise ValueError('皇冠颜色覆盖率无效')
            self.crown_slots.append((slot, box, empty))

    def validate_battle(self):
        if not self.profile.get('calibrated'):
            raise ValueError('请先校准识别配置，参见 docs/RULE_BATTLE.zh-CN.md')
        labels = {entry['label'] for entry, _, _ in self.templates}
        required = {'home_screen', 'game_mode_button_1', 'classic_1v1', 'battle_button',
                    'battle_screen', 'battle_end', 'continue_button'}
        if self.profile.get('require_mode_ready'):
            required.add('classic_mode_ready')
        if len(self.crown_slots) != 3:
            required.update(f'result_crowns_{i}' for i in range(4))
        if missing := required - labels:
            raise ValueError(f'缺少流程模板: {sorted(missing)}')
        if (len(self.profile.get('hand_rois', [])) != 4 or len(self.profile.get('elixir_rois', [])) != 10
            or any(roi is None for roi in self.profile.get('hand_rois', []) + self.profile.get('elixir_rois', []))):
            raise ValueError('需要四个手牌区域和十个圣水采样区域')
        from automation.games.clash_royale.rule_policy import RuleBattlePolicy
        RuleBattlePolicy(self.profile.get('deck', []))

    def detect(self, image: bytes) -> list[Detection]:
        frame = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('截图不是有效图片')
        height, width = frame.shape[:2]
        if abs((width / height) / (self.width / self.height) - 1) > .01:
            raise ValueError('截图宽高比与校准配置不同，请重新校准')
        frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)
        matches = {}
        for entry, template, (x1, y1, x2, y2) in self.templates:
            scores = cv2.matchTemplate(frame[y1:y2, x1:x2], template, cv2.TM_SQDIFF_NORMED)
            low, _, point, _ = cv2.minMaxLoc(scores)
            score = 1 - low
            if score < entry.get('threshold', .90):
                continue
            x, y = x1 + point[0], y1 + point[1]
            box = (x * width / self.width, y * height / self.height,
                   (x + template.shape[1]) * width / self.width, (y + template.shape[0]) * height / self.height)
            if 'target' in entry:
                box = roi_pixels(entry['target'], width, height)
            detection = Detection(entry['label'], score, box)
            if detection.confidence > matches.get(detection.label, Detection('', -1, box)).confidence:
                matches[detection.label] = detection
        # Ambiguous crowns must never be recorded as a confident result.
        crowns = [key for key in matches if key.startswith('result_crowns_')]
        if len(crowns) > 1:
            for key in crowns:
                del matches[key]
        if 'battle_end' in matches and len(self.crown_slots) == 3:
            values = []
            for slot, (x1, y1, x2, y2), empty in self.crown_slots:
                crop = frame[y1:y2, x1:x2]
                low, high = slot.get('active_hsv', [[15, 100, 100], [40, 255, 255]])
                active = np.mean(cv2.inRange(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV), np.array(low), np.array(high)) > 0) >= slot.get('active_coverage', .25)
                inactive = 1-float(cv2.matchTemplate(crop, empty, cv2.TM_SQDIFF_NORMED)[0, 0]) >= slot.get('empty_threshold', .95)
                if active == inactive:
                    break
                values.append(int(active))
            if len(values) == 3:
                matches['crowns'] = Detection(f'result_crowns_{sum(values)}', 1., (0, 0, 1, 1))
        if 'battle_screen' in matches and not any(k in matches for k in ('battle_end', 'victory_screen', 'defeat_screen')):
            regions = self.profile.get('elixir_rois', [])
            if len(regions) == 10 and all(roi is not None for roi in regions):
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                lower, upper = self.profile.get('elixir_hsv', [[125, 80, 80], [175, 255, 255]])
                count = 0
                for roi in regions:
                    x1, y1, x2, y2 = roi_pixels(roi, self.width, self.height)
                    coverage = np.mean(cv2.inRange(hsv[y1:y2, x1:x2], np.array(lower), np.array(upper)) > 0)
                    if coverage < self.profile.get('elixir_coverage', .6):
                        break
                    count += 1
                matches['elixir'] = Detection(f'elixir_{count}', 1.0, (0, 0, 1, 1))
        return list(matches.values())


def create_detector(settings):
    if settings.visionBackend == 'template':
        return ProfileDetector(settings.visionProfilePath)
    if settings.visionBackend == 'yolo':
        return VisionEngine(settings.modelPath, settings.yoloConfidence)
    raise ValueError(f'未知识别后端: {settings.visionBackend}')
