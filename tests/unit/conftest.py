from etcs_pipeline.models.linked_list import LinkedList, MessageNode, Direction
from etcs_pipeline.models.scenario import ScenarioFeatures, Position, Section


def build_message(
    nid_message: int,
    step: int = 1,
    scenario_params: dict | None = None,
    to_instantiate: list[str] | None = None,
    packets: list | None = None,
    name: str = "",
    direction: Direction = Direction.TRAIN_TO_RBC,
) -> MessageNode:
    return MessageNode(
        step=step,
        nid_message=nid_message,
        name=name or f"Msg{nid_message}",
        direction=direction,
        scenario_params=scenario_params or {},
        to_instantiate=to_instantiate or [],
        packets=packets or [],
    )


def build_linked_list(messages: list[MessageNode]) -> LinkedList:
    features = ScenarioFeatures(
        initial_mode="SR",
        initial_position=Position(bg_id=1001, distance_m=50),
        sections=[Section(length_m=500, v_max_kmh=80)],
        eoa_distance_m=3500,
    )
    return LinkedList(
        spec_version="subset026-3.6.0",
        scenario_features=features,
        messages=messages,
    )
