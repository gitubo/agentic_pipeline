import pytest
from etcs_pipeline.components.validator import FormalValidator
from etcs_pipeline.config.loader import ProfileLoader
from .conftest import build_message, build_linked_list
from etcs_pipeline.models.linked_list import Direction


@pytest.fixture
def validator():
    return FormalValidator(ProfileLoader("etcs"))


def test_valid_position_report(validator):
    ll = build_linked_list([build_message(
        nid_message=0,
        direction=Direction.TRAIN_TO_RBC,
        scenario_params={
            "Q_SCALE": 1, "D_LRBG": 50, "V_TRAIN": 0,
            "M_MODE": 3, "M_LEVEL": 2, "Q_LENGTH": 1,
        },
        to_instantiate=["T_TRAIN", "L_MESSAGE", "NID_LRBG", "M_ACK", "Q_DIRLRBG"],
    )])
    result = validator.validate(ll)
    assert result.valid


def test_missing_required_field(validator):
    ll = build_linked_list([build_message(
        nid_message=3,
        direction=Direction.RBC_TO_TRAIN,
        scenario_params={"Q_SCALE": 1, "N_ITER": 1},
        # V_RELEASESPEED missing
    )])
    result = validator.validate(ll)
    assert not result.valid
    assert any(e.error_code == "FIELD_REQUIRED_MISSING" and e.field == "V_RELEASESPEED"
               for e in result.errors)


def test_invalid_enum_value(validator):
    ll = build_linked_list([build_message(
        nid_message=0,
        direction=Direction.TRAIN_TO_RBC,
        scenario_params={
            "Q_SCALE": 99,  # not in [0, 1, 2]
            "D_LRBG": 50, "V_TRAIN": 0, "M_MODE": 3,
            "M_LEVEL": 2, "Q_LENGTH": 1,
        },
        to_instantiate=["T_TRAIN", "L_MESSAGE", "NID_LRBG", "M_ACK"],
    )])
    result = validator.validate(ll)
    assert not result.valid
    assert any(e.error_code == "FIELD_INVALID_ENUM_VALUE" for e in result.errors)


def test_conditional_field_required(validator):
    # Q_SECTIONTIMER==1 → T_SECTIONTIMER is required
    ll = build_linked_list([build_message(
        nid_message=3,
        direction=Direction.RBC_TO_TRAIN,
        scenario_params={
            "Q_SCALE": 1, "N_ITER": 1, "V_RELEASESPEED": 30,
            "Q_SECTIONTIMER": 1,
            # T_SECTIONTIMER missing → should produce an error
        },
        to_instantiate=["T_TRAIN", "L_MESSAGE", "NID_LRBG", "M_ACK"],
    )])
    result = validator.validate(ll)
    assert not result.valid
    assert any(e.error_code == "FIELD_REQUIRED_BY_CONDITION" and e.field == "T_SECTIONTIMER"
               for e in result.errors)


def test_unknown_message_type_is_warning(validator):
    ll = build_linked_list([build_message(nid_message=999)])
    result = validator.validate(ll)
    assert result.valid  # does not block
    assert any(e.error_code == "UNKNOWN_MESSAGE_TYPE" for e in result.warnings)
