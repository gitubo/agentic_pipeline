import pytest
from etcs_pipeline.components.instantiator import Instantiator
from etcs_pipeline.config.loader import ProfileLoader
from .conftest import build_message, build_linked_list
from etcs_pipeline.models.linked_list import Direction


@pytest.fixture
def instantiator():
    return Instantiator(ProfileLoader("etcs"))


def test_t_train_instantiated(instantiator):
    ll = build_linked_list([build_message(
        nid_message=0, step=1, direction=Direction.TRAIN_TO_RBC,
        to_instantiate=["T_TRAIN"],
    )])
    result = instantiator.complete(ll)
    msg = result.messages[0]
    assert "T_TRAIN" in msg.scenario_params
    assert isinstance(msg.scenario_params["T_TRAIN"], int)
    assert msg.scenario_params["T_TRAIN"] > 0


def test_t_train_increments(instantiator):
    ll = build_linked_list([
        build_message(nid_message=0, step=1, to_instantiate=["T_TRAIN"]),
        build_message(nid_message=3, step=2, to_instantiate=["T_TRAIN"]),
    ])
    result = instantiator.complete(ll)
    t1 = result.messages[0].scenario_params["T_TRAIN"]
    t2 = result.messages[1].scenario_params["T_TRAIN"]
    assert t2 > t1


def test_m_ack_for_position_report(instantiator):
    ll = build_linked_list([build_message(
        nid_message=0, step=1, to_instantiate=["M_ACK"],
    )])
    result = instantiator.complete(ll)
    assert result.messages[0].scenario_params["M_ACK"] == 0


def test_m_ack_for_movement_authority(instantiator):
    ll = build_linked_list([build_message(
        nid_message=3, step=1, direction=Direction.RBC_TO_TRAIN,
        to_instantiate=["M_ACK"],
    )])
    result = instantiator.complete(ll)
    assert result.messages[0].scenario_params["M_ACK"] == 1


def test_unknown_field_produces_placeholder(instantiator):
    ll = build_linked_list([build_message(
        nid_message=0, step=1, to_instantiate=["UNKNOWN_FIELD_XYZ"],
    )])
    result = instantiator.complete(ll)
    msg = result.messages[0]
    placeholder = msg.scenario_params.get("UNKNOWN_FIELD_XYZ")
    assert placeholder is not None
    assert isinstance(placeholder, dict)
    assert placeholder.get("flag") == "REQUIRES_EXPERT_INPUT"


def test_instantiated_fields_removed_from_to_instantiate(instantiator):
    ll = build_linked_list([build_message(
        nid_message=0, step=1, to_instantiate=["T_TRAIN", "Q_SCALE", "M_ACK"],
    )])
    result = instantiator.complete(ll)
    msg = result.messages[0]
    # All three are resolvable — to_instantiate should be empty
    assert msg.to_instantiate == []
