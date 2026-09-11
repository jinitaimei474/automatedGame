import pytest

from automation.core.tasks import CrownProgressTracker, StopReason


@pytest.mark.parametrize("crowns", [0, 1, 2, 3])
def test_round_crowns(crowns):
    tracker = CrownProgressTracker(5)
    assert tracker.record_result("result-a", crowns)
    assert tracker.earned_crowns == crowns
    assert tracker.round_count == 1


def test_duplicate_result_is_counted_once():
    tracker = CrownProgressTracker(5)
    assert tracker.record_result("same", 2)
    assert not tracker.record_result("same", 2)
    assert tracker.earned_crowns == 2
    assert tracker.round_count == 1


def test_overshoot_completes_and_keeps_real_value():
    tracker = CrownProgressTracker(5)
    tracker.record_result("one", 3)
    tracker.record_result("two", 3)
    assert tracker.earned_crowns == 6
    assert tracker.remaining_crowns == 0
    assert tracker.stop_reason == StopReason.TARGET_REACHED


def test_invalid_round_value_is_rejected():
    with pytest.raises(ValueError):
        CrownProgressTracker(5).record_result("bad", 4)

