from etcs_pipeline.models.linked_list import LinkedList, MessageNode
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult, ValidationError
from etcs_pipeline.config.loader import ProfileLoader


class StateMachineValidator:
    def __init__(self, loader: ProfileLoader):
        self._sm = loader.load_state_machine()
        self._valid_transitions: dict[tuple[str, str], dict] = {}
        for t in self._sm.get("transitions", []):
            self._valid_transitions[(t["from"], t["to"])] = t

        mt = self._sm.get("mode_tracking", {})
        self._mode_nid: int | None = mt.get("nid_message")
        self._mode_field: str | None = mt.get("field")
        self._session_carrier_nid: int | None = self._sm.get("session_carrier_nid_message")
        self._pre_session_guard: dict = self._sm.get("pre_session_guard", {})
        self._mode_requires_prior: dict = self._sm.get("mode_requires_prior_check", {})

    def check(self, ll: LinkedList, features: ScenarioFeatures) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        messages = ll.messages

        # Mode transition tracking
        if self._mode_nid is not None and self._mode_field:
            modes_seen: list[tuple[int, str, MessageNode]] = []
            for msg in messages:
                if msg.nid_message == self._mode_nid:
                    raw_mode = msg.scenario_params.get(self._mode_field)
                    if raw_mode is not None:
                        mode_id = self._m_mode_to_id(raw_mode)
                        if mode_id:
                            modes_seen.append((msg.step, mode_id, msg))

            for i in range(1, len(modes_seen)):
                _, prev_mode, _ = modes_seen[i - 1]
                curr_step, curr_mode, curr_msg = modes_seen[i]
                if prev_mode != curr_mode and (prev_mode, curr_mode) not in self._valid_transitions:
                    errors.append(ValidationError(
                        step=curr_step,
                        message_name=curr_msg.name,
                        nid_message=curr_msg.nid_message,
                        field=self._mode_field,
                        error_code="STATE_ILLEGAL_TRANSITION",
                        description=(
                            f"Mode transition {prev_mode}→{curr_mode} is not "
                            f"defined in the state machine"
                        ),
                        spec_ref=self._transition_spec(prev_mode, curr_mode),
                    ))

        # Pre-session guard
        guard = self._pre_session_guard
        if guard and self._session_carrier_nid is not None:
            guarded_nid = guard.get("guarded_nid_message")
            session_step = self._find_session_step(messages)
            if guarded_nid is not None and session_step is not None:
                for msg in messages:
                    if msg.nid_message == guarded_nid and msg.step < session_step:
                        errors.append(ValidationError(
                            step=msg.step,
                            message_name=msg.name,
                            nid_message=msg.nid_message,
                            field=None,
                            error_code=guard.get("error_code", "STATE_BEFORE_SESSION"),
                            description=(
                                f"Message {msg.name} sent before session was established"
                            ),
                            spec_ref=guard.get("spec_ref", ""),
                        ))

        # Mode requires a prior message
        mrp = self._mode_requires_prior
        if mrp and self._mode_nid is not None and self._mode_field:
            req_mode = mrp.get("mode_value")
            prior_nid = mrp.get("prior_nid_message")
            if req_mode is not None and prior_nid is not None:
                prior_steps = [m.step for m in messages if m.nid_message == prior_nid]
                prior_first = min(prior_steps) if prior_steps else None
                for msg in messages:
                    if (
                        msg.nid_message == self._mode_nid
                        and msg.scenario_params.get(self._mode_field) == req_mode
                        and (prior_first is None or msg.step < prior_first)
                    ):
                        errors.append(ValidationError(
                            step=msg.step,
                            message_name=msg.name,
                            nid_message=msg.nid_message,
                            field=self._mode_field,
                            error_code=mrp.get("error_code", "STATE_MODE_REQUIRES_PRIOR"),
                            description=(
                                f"{self._mode_field}={req_mode} without a preceding "
                                f"NID_MESSAGE={prior_nid} message"
                            ),
                            spec_ref=mrp.get("spec_ref", ""),
                        ))

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _m_mode_to_id(self, m_mode_value: int) -> str | None:
        for state in self._sm.get("states", []):
            if state.get("m_mode_value") == m_mode_value:
                return state["id"]
        return None

    def _find_session_step(self, messages: list[MessageNode]) -> int | None:
        if self._session_carrier_nid is None:
            return None
        for msg in messages:
            if msg.nid_message == self._session_carrier_nid:
                return msg.step
        return None

    def _transition_spec(self, from_mode: str, to_mode: str) -> str:
        return self._valid_transitions.get((from_mode, to_mode), {}).get("spec_ref", "")
