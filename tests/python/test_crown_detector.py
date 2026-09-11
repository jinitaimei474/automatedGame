import pytest

from automation.core.vision import Detection
from automation.games.clash_royale.detectors import CrownConfirmationError, CrownResultDetector


def frame(value: int):
    return [Detection(f"result_crowns_{value}", 0.95, (0, 0, 10, 10))]


def test_three_matching_frames_confirm():
    assert CrownResultDetector(3).confirm_frames([frame(2), frame(2), frame(2)]) == 2


def test_inconsistent_frames_do_not_guess():
    with pytest.raises(CrownConfirmationError):
        CrownResultDetector(3).confirm_frames([frame(1), frame(2), frame(1)])


def test_low_confidence_does_not_confirm():
    weak = [Detection("result_crowns_1", 0.2, (0, 0, 10, 10))]
    with pytest.raises(CrownConfirmationError):
        CrownResultDetector(2, 0.75).confirm_frames([weak, weak])

