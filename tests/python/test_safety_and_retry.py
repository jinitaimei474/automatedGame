import asyncio

from automation.core.events import EventBus
from automation.core.safety import SafetyGuard, SafetyViolation
from automation.core.vision import Detection
from automation.core.workflow import CancellationToken, WorkflowEngine
from automation.games.clash_royale.tasks import DailyShopFreeItemTask


def detection(label: str):
    return Detection(label, 0.99, (0, 0, 10, 10))


def test_paid_content_is_never_claimable():
    guard = SafetyGuard()
    try:
        guard.can_claim_free_item([detection("daily_trader"), detection("free_label"), detection("currency_price")])
        assert False, "SafetyViolation expected"
    except SafetyViolation:
        pass


def test_daily_task_pauses_on_payment_confirmation():
    async def scenario():
        events = []; bus = EventBus(); bus.on_any(events.append)
        task = DailyShopFreeItemTask(bus, CancellationToken())
        result = await task.evaluate_shop([detection("daily_trader"), detection("free_item"), detection("free_label"), detection("payment_confirmation")])
        return result, events
    result, events = asyncio.run(scenario())
    assert result == "PAUSED"
    assert any(event["type"] == "task_paused" for event in events)


def test_retry_has_hard_limit():
    async def scenario():
        calls = 0; engine = WorkflowEngine(EventBus(), CancellationToken())
        async def fail():
            nonlocal calls; calls += 1; return False
        result = await engine.retry(fail, max_retries=2, delay=0)
        return result, calls
    assert asyncio.run(scenario()) == (False, 3)

