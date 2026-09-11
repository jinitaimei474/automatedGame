import pytest

from automation.core.tasks import ParameterValidationError, TaskParameter, validate_parameters

SCHEMA = (TaskParameter("targetCrowns", "目标皇冠数量", "integer", True, 10, 1, 9999),)


@pytest.mark.parametrize("value", [None, "", 0, -1, 1.5, "5", 10000, True])
def test_invalid_target_crowns(value):
    with pytest.raises(ParameterValidationError):
        validate_parameters(SCHEMA, {"targetCrowns": value})


@pytest.mark.parametrize("value", [1, 10, 9999])
def test_valid_target_crowns(value):
    assert validate_parameters(SCHEMA, {"targetCrowns": value})["targetCrowns"] == value

