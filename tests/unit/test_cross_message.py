import pytest
from etcs_pipeline.components.plausibility.cross_message import CrossMessageChecker
from etcs_pipeline.config.loader import ProfileLoader
from .conftest import build_message, build_linked_list
from etcs_pipeline.models.linked_list import Direction


@pytest.fixture
def cross_checker():
    return CrossMessageChecker(ProfileLoader("etcs"))


def test_consistent_qscale(cross_checker):
    ll = build_linked_list([
        build_message(nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"Q_SCALE": 1}),
        build_message(nid_message=3, step=2, direction=Direction.RBC_TO_TRAIN,
                      scenario_params={"Q_SCALE": 1}),
    ])
    result = cross_checker.check(ll, ll.scenario_features)
    assert result.valid


def test_inconsistent_qscale(cross_checker):
    ll = build_linked_list([
        build_message(nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"Q_SCALE": 1}),
        build_message(nid_message=3, step=2, direction=Direction.RBC_TO_TRAIN,
                      scenario_params={"Q_SCALE": 2}),
    ])
    result = cross_checker.check(ll, ll.scenario_features)
    assert not result.valid
    assert any(e.error_code == "CROSS_SESSION_FIELD_INCONSISTENT" for e in result.errors)


def test_no_qscale_no_error(cross_checker):
    # No message carries Q_SCALE — no consistency error expected
    ll = build_linked_list([
        build_message(nid_message=8, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"T_TRAIN_ref": 100}),
    ])
    result = cross_checker.check(ll, ll.scenario_features)
    assert result.valid
