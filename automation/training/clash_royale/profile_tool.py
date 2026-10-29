"""Author local templates from screenshots, without bounding-box datasets.

Run ``python -m automation.training.clash_royale.profile_tool --help``.
All rectangles are x1 y1 x2 y2 pixels in the reference screenshot.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from automation.core.vision import annotate_detections
from automation.core.vision.profile import ProfileDetector
from automation.games.clash_royale.rule_policy import RuleBattlePolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='config/clash_royale/profile.json')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--image', required=True)
    for name in ('template', 'card', 'region'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--image', required=True)
        cmd.add_argument('--roi', nargs=4, type=int, required=True)
        if name == 'template':
            cmd.add_argument('--label', required=True)
        elif name == 'card':
            cmd.add_argument('--name', required=True)
            cmd.add_argument('--cost', type=int, required=True)
            cmd.add_argument('--placement', nargs=2, type=float, required=True)
            cmd.add_argument('--priority', type=int, default=0)
        else:
            cmd.add_argument('--kind', choices=['hand', 'elixir'], required=True)
            cmd.add_argument('--index', type=int, required=True)
    preview = commands.add_parser('preview')
    preview.add_argument('--image', required=True)
    preview.add_argument('--output', required=True)
    commands.add_parser('activate', help='结构检查后启用；仅在预览校准完成后执行')
    args = parser.parse_args()
    path = Path(args.profile)
    if args.command == 'init' and path.exists():
        parser.error('配置已经存在，不会覆盖')
    profile = {} if args.command == 'init' else json.loads(path.read_text(encoding='utf-8'))
    if hasattr(args, 'image'):
        image = Path(args.image).read_bytes()
        frame = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            parser.error('截图不可读')
        height, width = frame.shape[:2]
        if args.command not in ('init', 'preview') and profile['resolution'] != [width, height]:
            parser.error('模板截图必须和参考分辨率相同')
    if args.command == 'init':
        profile = {'resolution': [width, height], 'calibrated': False, 'templates': [],
                   'deck': [], 'hand_rois': [None]*4, 'elixir_rois': [None]*10,
                   'elixir_hsv': [[125, 80, 80], [175, 255, 255]], 'elixir_coverage': .6}
    elif args.command in ('template', 'card', 'region'):
        x1, y1, x2, y2 = args.roi
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            parser.error('裁剪区域越界')
        roi = [x1/width, y1/height, x2/width, y2/height]
        if args.command == 'region':
            regions = profile[f'{args.kind}_rois']
            if not 0 <= args.index < len(regions):
                parser.error('区域索引越界')
            regions[args.index] = roi
        else:
            name = args.label if args.command == 'template' else args.name
            if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name):
                parser.error('名称仅允许小写字母、数字和下划线')
            relative = f'templates/{args.command}_{name}.png'
            target = path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(cv2.imencode('.png', frame[y1:y2, x1:x2])[1].tobytes())
            if args.command == 'template':
                entry = {'label': name, 'file': relative, 'roi': roi, 'threshold': .90}
                profile['templates'] = [t for t in profile['templates'] if t['label'] != name] + [entry]
            else:
                entry = {'name': name, 'file': relative, 'cost': args.cost,
                         'placement': args.placement, 'priority': args.priority, 'threshold': .90}
                profile['deck'] = [c for c in profile['deck'] if c['name'] != name] + [entry]
        profile['calibrated'] = False
    elif args.command == 'preview':
        detections = ProfileDetector(path).detect(image)
        Path(args.output).write_bytes(annotate_detections(image, detections))
        print(json.dumps([d.as_dict() for d in detections], ensure_ascii=False, indent=2))
        return
    elif args.command == 'activate':
        detector = ProfileDetector(path)
        detector.profile['calibrated'] = True
        detector.validate_battle()
        RuleBattlePolicy(profile.get('deck', []))
        profile['calibrated'] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'已保存: {path}')


if __name__ == '__main__':
    main()
