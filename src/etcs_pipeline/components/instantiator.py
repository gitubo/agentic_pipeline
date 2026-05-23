from etcs_pipeline.models.linked_list import LinkedList, MessageNode
from etcs_pipeline.config.loader import ProfileLoader


class Instantiator:
    def __init__(self, loader: ProfileLoader):
        data = loader.load_defaults()
        self._session_defaults: dict = data.get("session", {})
        self._per_message: dict[int, dict] = {
            m["nid_message"]: m.get("fields", {})
            for m in data.get("per_message", [])
        }
        self._per_packet: dict[int, dict] = {
            p["nid_packet"]: p.get("fields", {})
            for p in data.get("per_packet", [])
        }
        self._t_train_step_ms: int = data.get("session", {}).get("T_TRAIN_step_ms", 100)

    def complete(self, linked_list: LinkedList) -> LinkedList:
        ll = linked_list.model_copy(deep=True)
        t_train_base = 0

        for msg in ll.messages:
            t_train_base += self._t_train_step_ms
            self._complete_message(msg, t_train_base)

        return ll

    def _complete_message(self, msg: MessageNode, t_train: int) -> None:
        remaining = []
        for field in msg.to_instantiate:
            value = self._resolve_field(field, msg.nid_message, t_train)
            if value is not None:
                msg.scenario_params[field] = value
            else:
                msg.scenario_params[field] = {
                    "value": None,
                    "flag": "REQUIRES_EXPERT_INPUT",
                    "note": (
                        f"Field {field} has no configured default "
                        f"for NID_MESSAGE={msg.nid_message}"
                    ),
                }
                remaining.append(field)

        msg.to_instantiate = remaining

        for packet in msg.packets:
            pkt_defaults = self._per_packet.get(packet.nid_packet, {})
            for field, value in pkt_defaults.items():
                if field not in packet.scenario_params:
                    packet.scenario_params[field] = value

    def _resolve_field(self, field: str, nid_message: int, t_train: int) -> object:
        if field == "T_TRAIN":
            return t_train
        if field in self._session_defaults:
            return self._session_defaults[field]
        per_msg = self._per_message.get(nid_message, {})
        if field in per_msg:
            return per_msg[field]
        return None
