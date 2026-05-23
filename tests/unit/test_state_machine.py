import pytest
from etcs_pipeline.components.plausibility.state_machine import StateMachineValidator
from etcs_pipeline.config.loader import ProfileLoader
from .conftest import build_message, build_linked_list
from etcs_pipeline.models.linked_list import Direction


@pytest.fixture
def sm_validator():
    return StateMachineValidator(ProfileLoader("etcs"))


def test_valid_sr_to_fs_sequence(sm_validator):
    # SR (M_MODE=3) → MA → ACK → FS (M_MODE=0)
    ll = build_linked_list([
        build_message(nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"M_MODE": 3}),
        build_message(nid_message=3, step=2, direction=Direction.RBC_TO_TRAIN,
                      scenario_params={"Q_SCALE": 1, "N_ITER": 1, "V_RELEASESPEED": 30}),
        build_message(nid_message=8, step=3, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"T_TRAIN_ref": 200}),
        build_message(nid_message=0, step=4, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"M_MODE": 0}),
    ])
    result = sm_validator.check(ll, ll.scenario_features)
    assert result.valid


def test_fs_without_ma(sm_validator):
    # PositionReport in FS mode without a preceding MA
    ll = build_linked_list([
        build_message(nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"M_MODE": 0}),  # FS without MA
    ])
    result = sm_validator.check(ll, ll.scenario_features)
    assert not result.valid
    assert any(e.error_code == "STATE_FS_WITHOUT_MA" for e in result.errors)


def test_illegal_transition(sm_validator):
    # NP → FS is not a defined transition
    ll = build_linked_list([
        build_message(nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"M_MODE": 8}),  # NP
        build_message(nid_message=3, step=2, direction=Direction.RBC_TO_TRAIN,
                      scenario_params={}),
        build_message(nid_message=0, step=3, direction=Direction.TRAIN_TO_RBC,
                      scenario_params={"M_MODE": 0}),  # FS — transition NP→FS not defined
    ])
    result = sm_validator.check(ll, ll.scenario_features)
    assert not result.valid
    assert any(e.error_code == "STATE_ILLEGAL_TRANSITION" for e in result.errors)
