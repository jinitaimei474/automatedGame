import json

import cv2
import numpy as np
import pytest

from automation.core.vision.profile import ProfileDetector
from automation.games.clash_royale.rule_policy import RuleBattlePolicy
from automation.core.vision import Detection


def encode(frame):
    return cv2.imencode('.png', frame)[1].tobytes()


@pytest.mark.parametrize('anchored', [False, True])
def test_template_roi_and_scaled_click(tmp_path, anchored):
    rng = np.random.default_rng(2)
    template = rng.integers(0, 255, (10, 12, 3), dtype=np.uint8)
    (tmp_path / 'button.png').write_bytes(encode(template))
    profile = {'resolution': [100, 200], 'templates': [
        {'label': 'battle_button', 'file': 'button.png', 'roi': [0, .5, 1, 1]}]}
    if anchored:
        profile['templates'][0]['target'] = [.6, .2, .8, .4]
    (tmp_path / 'profile.json').write_text(json.dumps(profile))
    detector = ProfileDetector(tmp_path / 'profile.json')
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    frame[130:140, 20:32] = template
    result = detector.detect(encode(cv2.resize(frame, (200, 400), interpolation=cv2.INTER_NEAREST)))
    assert result[0].label == 'battle_button'
    assert result[0].center == ((140, 120) if anchored else (52, 270))
    frame[:] = 0
    assert detector.detect(encode(frame)) == []
    with pytest.raises(ValueError, match='宽高比'):
        detector.detect(encode(np.zeros((100, 200, 3), dtype=np.uint8)))


def test_missing_template_fails_at_startup(tmp_path):
    path = tmp_path / 'p.json'
    path.write_text(json.dumps({'resolution': [100, 200], 'templates': [
        {'label': 'battle_screen', 'file': 'missing.png', 'roi': [0, 0, 1, 1]}]}))
    with pytest.raises(ValueError, match='missing.png'):
        ProfileDetector(path)


def d(label):
    return Detection(label, .99, (10, 20, 30, 40))


def deck():
    return [{'name': f'card{i}', 'cost': i + 1, 'placement': [.3, .7], 'priority': 8-i} for i in range(8)]


def test_policy_affordability_acknowledgement_and_unknown_state():
    policy = RuleBattlePolicy(deck(), cooldown=1, acknowledgement_timeout=3)
    frame = [d('battle_screen'), d('elixir_3'), d('card_0_card0'), d('card_1_card7')]
    move = policy.choose(frame, 0)
    assert move.card == 'card0' and move.slot == 0
    policy.submitted(move, frame, 0)
    assert policy.choose(frame, 2) is None  # unchanged hand: do not spam taps
    with pytest.raises(RuntimeError, match='出牌未确认'):
        policy.choose(frame, 4)
    policy.reset()
    assert policy.choose([d('elixir_10'), d('card_0_card0')], 5) is None
    assert policy.choose(frame + [d('battle_end')], 5) is None
    policy.reset()
    move = policy.choose(frame, 0)
    policy.submitted(move, frame, 0)
    changed = [d('battle_screen'), d('elixir_2'), d('card_0_card1')]
    assert policy.choose(changed, 2).card == 'card1'


def test_conflicting_card_or_elixir_evidence_does_not_play():
    policy = RuleBattlePolicy(deck())
    assert policy.choose([d('battle_screen'), d('elixir_3'), d('elixir_9'), d('card_0_card0')], 0) is None
    assert policy.choose([d('battle_screen'), d('elixir_9'), d('card_0_card0'), d('card_0_card1')], 0) is None


@pytest.mark.parametrize('end_while_selected', [False, True])
@pytest.mark.parametrize('by_rounds', [False, True])
def test_live_two_matches_taps_and_stops_at_round_cap(monkeypatch, end_while_selected, by_rounds):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live

    class Vision:
        profile = {'deck': deck()}
        def validate_battle(self):
            pass

    monkeypatch.setattr(live, 'create_detector', lambda settings: Vision())
    task = live.LiveClassic1v1Task(10, AppSettings(maxRounds=2, gameLaunchWaitSeconds=0,
        crownConfirmationFrames=1, inferenceIntervalMs=1), EventBus(), CancellationToken(), target_rounds=2 if by_rounds else None)
    taps = []
    class Adb:
        async def resolution(self):
            return 100, 200
        async def start_app(self, *args):
            pass
        async def tap(self, x, y):
            taps.append((x, y))
    task.adb = Adb()
    task.actions.adb = task.adb
    task.actions.safe_offset = 0
    states = ['home_screen', 'game_mode_button_1', 'game_mode_button_1',
              'classic_1v1', 'classic_1v1', 'classic_1v1']
    for round_index in range(2):
        states += ['battle_button', 'battle_button', 'battle_screen', 'battle_screen',
                   'playing', 'battle_end' if end_while_selected else 'playing', 'battle_end', 'result_crowns_0']
        if round_index == 0:
            states += ['continue_button', 'continue_button', 'continue_button', 'battle_button']
    async def capture():
        state = states.pop(0)
        detections = [d('battle_screen'), d('elixir_3'), d('card_0_card0')] if state == 'playing' else [d(state)]
        if by_rounds and state == 'result_crowns_0':
            detections = [d('battle_end')]  # rounds must not depend on crown recognition
        return encode(np.zeros((200, 100, 3), np.uint8)), detections
    task._capture = capture
    result = asyncio.run(task.run())
    assert result.round_count == 2
    assert result.stop_reason.value == ('TARGET_REACHED' if by_rounds else 'ROUND_LIMIT')
    assert taps.count((30, 140)) == (0 if end_while_selected else 2)
    assert states == []


def test_stopping_while_paused_unblocks_checkpoint():
    import asyncio
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken, CancelledError, WorkflowEngine

    async def run():
        token = CancellationToken()
        engine = WorkflowEngine(EventBus(), token)
        await engine.pause()
        waiting = asyncio.create_task(engine.checkpoint())
        await asyncio.sleep(.01)
        token.cancel()
        with pytest.raises(CancelledError):
            await asyncio.wait_for(waiting, .5)
    asyncio.run(run())


def test_color_elixir_and_conflicting_crowns(tmp_path):
    rng = np.random.default_rng(3)
    anchor = rng.integers(0, 255, (10, 10, 3), dtype=np.uint8)
    (tmp_path / 'anchor.png').write_bytes(encode(anchor))
    p = {'resolution': [100, 200], 'templates': [
        {'label': 'battle_screen', 'file': 'anchor.png', 'roi': [0, 0, .1, .05]}],
        'elixir_rois': [[i/10, .9, (i+1)/10, .95] for i in range(10)]}
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(p))
    frame = np.zeros((200, 100, 3), np.uint8)
    frame[:10, :10] = anchor
    frame[180:190, :30] = [255, 0, 255]
    assert 'elixir_3' in {d.label for d in ProfileDetector(path).detect(encode(frame))}
    for value in (1, 2):
        p['templates'].append({'label': f'result_crowns_{value}', 'file': 'anchor.png', 'roi': [0, 0, .1, .05]})
    path.write_text(json.dumps(p))
    assert not any(d.label.startswith('result_crowns_') for d in ProfileDetector(path).detect(encode(frame)))


@pytest.mark.parametrize('coverage', [0, -1, 1.1])
def test_invalid_color_coverage_is_rejected(tmp_path, coverage):
    path = tmp_path / 'p.json'
    path.write_text(json.dumps({'resolution': [100, 200], 'elixir_coverage': coverage}))
    with pytest.raises(ValueError, match='coverage'):
        ProfileDetector(path)


def test_pause_during_capture_discards_stale_card_action(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile = {'deck': deck()}
        def validate_battle(self):
            pass
    monkeypatch.setattr(live, 'create_detector', lambda settings: Vision())
    task = live.LiveClassic1v1Task(10, AppSettings(), EventBus(), CancellationToken())
    taps = []
    class Adb:
        async def tap(self, *point):
            taps.append(point)
    task.adb = Adb()
    captures = 0
    async def capture():
        nonlocal captures
        captures += 1
        if captures == 1:
            await task.engine.pause()
            async def resume():
                await asyncio.sleep(.01)
                await task.engine.resume()
            asyncio.create_task(resume())
            return b'', [d('battle_screen'), d('elixir_3'), d('card_0_card0')]
        return b'', [d('battle_end')]
    task._capture = capture
    asyncio.run(task._wait_battle_end())
    assert taps == []


def test_profile_tool_can_preview_partial_calibration(tmp_path, monkeypatch):
    from automation.training.clash_royale.profile_tool import main
    path, screenshot, output = tmp_path / 'profile.json', tmp_path / 'screen.png', tmp_path / 'preview.png'
    screenshot.write_bytes(encode(np.random.default_rng(1).integers(0, 255, (200, 100, 3), dtype=np.uint8)))
    def invoke(*args):
        monkeypatch.setattr('sys.argv', ['profile_tool', '--profile', str(path), *args])
        main()
    invoke('init', '--image', str(screenshot))
    invoke('template', '--image', str(screenshot), '--label', 'home_screen', '--roi', '10', '20', '30', '40')
    invoke('preview', '--image', str(screenshot), '--output', str(output))
    assert output.is_file()
    assert json.loads(path.read_text())['calibrated'] is False


def test_live_acknowledgement_uses_fresh_preplacement_elixir(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile = {'deck': deck()}
        def validate_battle(self):
            pass
    monkeypatch.setattr(live, 'create_detector', lambda settings: Vision())
    task = live.LiveClassic1v1Task(10, AppSettings(), EventBus(), CancellationToken())
    taps = []
    class Adb:
        async def tap(self, *point):
            taps.append(point)
    task.adb = Adb()
    frames = [
        [d('battle_screen'), d('elixir_3'), d('card_0_card0')],
        [d('battle_screen'), d('elixir_4'), d('card_0_card0')],
        [d('battle_screen'), d('elixir_3'), d('card_0_card1')],
        [d('battle_end')],
    ]
    async def capture():
        return encode(np.zeros((200, 100, 3), np.uint8)), frames.pop(0)
    task._capture = capture
    asyncio.run(task._wait_battle_end())
    assert task.policy.pending is None
    assert len(taps) == 2


def test_crown_slots_require_positive_evidence_for_each_slot(tmp_path):
    anchor = np.random.default_rng(1).integers(0, 255, (10, 10, 3), dtype=np.uint8)
    (tmp_path / 'end.png').write_bytes(encode(anchor))
    empty = np.full((10, 10, 3), [255, 100, 0], np.uint8)
    (tmp_path / 'empty.png').write_bytes(encode(empty))
    profile = {'resolution': [100, 200], 'templates': [{'label': 'battle_end', 'file': 'end.png', 'roi': [0, 0, .1, .05]}],
               'crown_slots': [{'roi': [i*.2, .5, i*.2+.1, .55], 'empty_file': 'empty.png', 'active_hsv': [[15, 100, 100], [40, 255, 255]], 'active_coverage': .5} for i in range(3)]}
    path = tmp_path / 'p.json'; path.write_text(json.dumps(profile))
    frame = np.zeros((200, 100, 3), np.uint8); frame[:10, :10] = anchor
    for i in range(3): frame[100:110,i*20:i*20+10] = empty
    detector = ProfileDetector(path)
    assert 'result_crowns_0' in {x.label for x in detector.detect(encode(frame))}
    frame[100:110, :10] = [0, 255, 255]
    assert 'result_crowns_1' in {x.label for x in detector.detect(encode(frame))}
    frame[100:110, 20:30] = 0
    assert not any(x.label.startswith('result_crowns_') for x in detector.detect(encode(frame)))


def test_replacement_must_be_consistent_when_elixir_has_regenerated():
    policy = RuleBattlePolicy(deck())
    initial = [d('battle_screen'), d('elixir_3'), d('card_0_card0')]
    policy.submitted(policy.choose(initial, 0), initial, 0)
    replacement = [d('battle_screen'), d('elixir_3'), d('card_0_card1')]
    assert policy.choose(replacement, 2) is None
    assert policy.choose(initial, 3) is None  # transient match resets confirmation
    assert policy.choose(replacement, 4) is None
    assert policy.choose(replacement, 5).card == 'card1'
    assert policy.pending is None


def test_restart_at_result_recovers_without_starting_an_extra_match(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile = {'deck': deck()}
        def validate_battle(self): pass
    monkeypatch.setattr(live, 'create_detector', lambda settings: Vision())
    task = live.LiveClassic1v1Task(10, AppSettings(maxRounds=1, gameLaunchWaitSeconds=0,
        crownConfirmationFrames=1), EventBus(), CancellationToken())
    class Adb:
        async def resolution(self): return 100, 200
        async def start_app(self, *args): pass
        async def tap(self, *args): pytest.fail('recovery must not start another match')
    task.adb = Adb()
    task.actions.adb = task.adb
    states = ['battle_end', 'battle_end', 'result_crowns_0']
    async def capture(): return b'', [d(states.pop(0))]
    task._capture = capture
    result = asyncio.run(task.run())
    assert result.round_count == 1
    assert result.stop_reason.value == 'ROUND_LIMIT'
    assert not states


def test_card_portrait_variants_share_one_slot_identity(tmp_path):
    rng = np.random.default_rng(8)
    normal = rng.integers(0, 255, (10, 10, 3), dtype=np.uint8)
    evolved = rng.integers(0, 255, (10, 10, 3), dtype=np.uint8)
    (tmp_path/'normal.png').write_bytes(encode(normal))
    (tmp_path/'evolved.png').write_bytes(encode(evolved))
    path = tmp_path/'p.json'
    path.write_text(json.dumps({'resolution':[100,200], 'hand_rois':[[0,.5,.5,1]],
        'deck':[{'name':'cannon','file':'normal.png','variants':['evolved.png'],'threshold':.99}]}))
    detector = ProfileDetector(path)
    for portrait in (normal,evolved):
        frame = np.zeros((200,100,3),np.uint8)
        frame[130:140,20:30] = portrait
        result = detector.detect(encode(frame))
        assert [x.label for x in result] == ['card_0_cannon']


def test_click_waits_until_target_stops_moving(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile = {'deck':deck()}
        def validate_battle(self): pass
    monkeypatch.setattr(live,'create_detector',lambda settings:Vision())
    task=live.LiveClassic1v1Task(10,AppSettings(),EventBus(),CancellationToken())
    frames=[Detection('classic_1v1',.99,(0,0,20,20)),Detection('classic_1v1',.99,(0,100,20,120)),Detection('classic_1v1',.99,(0,100,20,120))]
    taps=[]
    async def wait(*args,**kwargs): return b'',frames.pop(0)
    async def sleep(*args): pass
    async def click(detection):
        assert not frames
        taps.append(detection.center)
    task._wait_detection=wait
    task.token.sleep=sleep
    task.actions.click_detection=click
    asyncio.run(task._confirmed_click(('classic_1v1',)))
    assert taps==[(10,110)]


def test_unconfirmed_card_does_not_abort_round(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile={'deck':deck()}
        def validate_battle(self): pass
    monkeypatch.setattr(live,'create_detector',lambda settings:Vision())
    bus=EventBus(); events=[]; bus.on_any(lambda e:events.append(e))
    task=live.LiveClassic1v1Task(9999,AppSettings(),bus,CancellationToken(),target_rounds=2)
    frames=[[d('battle_screen')],[d('battle_end')]]
    async def capture(): return b'',frames.pop(0)
    async def sleep(*args): pass
    def choose(*args): raise RuntimeError('出牌未确认')
    task._capture=capture;task.token.sleep=sleep;task.policy.choose=choose
    asyncio.run(task._wait_battle_end())
    assert not frames
    assert any(e['type']=='log_message' and e['payload']['level']=='WARNING' for e in events)
    assert not any(e['type']=='task_paused' for e in events)


def test_new_round_task_discards_previous_settlement(monkeypatch):
    import asyncio
    from automation.core.config import AppSettings
    from automation.core.events import EventBus
    from automation.core.workflow import CancellationToken
    from automation.games.clash_royale.tasks import live_classic_1v1 as live
    class Vision:
        profile={'deck':deck()}
        def validate_battle(self): pass
    monkeypatch.setattr(live,'create_detector',lambda settings:Vision())
    task=live.LiveClassic1v1Task(9999,AppSettings(gameLaunchWaitSeconds=0),EventBus(),CancellationToken(),target_rounds=1)
    class Adb:
        async def resolution(self): return 100,200
        async def start_app(self,*args): pass
    task.adb=Adb()
    calls=[]; first=True
    async def wait(labels,**kwargs):
        nonlocal first
        if first:
            first=False
            return b'',d('battle_end')
        return b'',d('battle_screen')
    async def prepare(): calls.append('dismiss-old')
    async def click(labels):
        assert labels==('battle_button','play_again_button')
        calls.append('start-new')
    async def battle(): calls.append('finish-new')
    async def confirm(): return 'new-result',None
    task._wait_detection=wait;task._prepare_next_round=prepare;task._confirmed_click=click
    task._wait_battle_end=battle;task._confirm_crown_result=confirm
    result=asyncio.run(task.run())
    assert calls==['dismiss-old','start-new','finish-new']
    assert result.round_count==1 and result.target_reached
