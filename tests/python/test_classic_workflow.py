import asyncio

from automation.core.events import EventBus
from automation.core.tasks import StopReason
from automation.core.workflow import CancellationToken
from automation.games.clash_royale.tasks import Classic1v1LoopTask


def run_scenario(target, rounds):
    async def scenario():
        events = []; bus = EventBus(); bus.on_any(events.append)
        task = Classic1v1LoopTask(target, bus, CancellationToken(), rounds)
        progress = await task.run()
        return task, progress, events
    return asyncio.run(scenario())


def test_complete_mock_scenario_1_2_2_stops_at_five():
    task, progress, events = run_scenario(5, [1, 2, 2, 3])
    assert progress.earned_crowns == 5
    assert progress.round_count == 3
    assert progress.stop_reason == StopReason.TARGET_REACHED
    assert task.next_round_count == 2
    assert any(event["type"] == "task_target_reached" for event in events)


def test_overshoot_scenario_shows_six_of_five():
    task, progress, _events = run_scenario(5, [3, 3, 3])
    assert progress.earned_crowns == 6
    assert progress.target_crowns == 5
    assert progress.round_count == 2
    assert task.next_round_count == 1


def test_target_reached_never_enters_next_round_after_completion():
    _task, _progress, events = run_scenario(1, [1, 3])
    states = [event["payload"].get("state") for event in events if event["type"] == "task_state_changed"]
    reached_index = states.index("TARGET_REACHED")
    assert "START_NEXT_ROUND" not in states[reached_index:]


def test_manual_stop_reason_is_distinct():
    async def scenario():
        bus = EventBus(); task = Classic1v1LoopTask(99, bus, CancellationToken(), [1] * 100)
        runner = asyncio.create_task(task.run()); await asyncio.sleep(0.03); task.stop(); return await runner
    progress = asyncio.run(scenario())
    assert progress.stop_reason == StopReason.USER_STOPPED

