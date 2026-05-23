from etcs_pipeline.models.linked_list import LinkedList
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult, ValidationError
from etcs_pipeline.config.loader import ProfileLoader


class CrossMessageChecker:
    def __init__(self, loader: ProfileLoader):
        data = loader.load_crossmessage_rules()
        self._rules: list[dict] = data.get("rules", [])

    def check(self, ll: LinkedList, features: ScenarioFeatures) -> ValidationResult:
        errors = []
        msgs_by_nid: dict[int, list] = {}
        for msg in ll.messages:
            msgs_by_nid.setdefault(msg.nid_message, []).append(msg)

        for rule in self._rules:
            check = rule.get("check", {})
            scope = check.get("scope")

            if scope == "session":
                field = check["field"]
                values = []
                for msg in ll.messages:
                    if field in msg.scenario_params:
                        values.append(msg.scenario_params[field])
                if len(set(values)) > 1:
                    errors.append(ValidationError(
                        step=-1,
                        message_name="session",
                        nid_message=-1,
                        field=field,
                        error_code="CROSS_SESSION_FIELD_INCONSISTENT",
                        description=(
                            f"{rule['name']}: {rule['description']} — "
                            f"valori trovati: {set(values)}"
                        ),
                        spec_ref="",
                    ))

            elif "message_a" in check and "message_b" in check:
                msg_a_nid = check["message_a"]["nid_message"]
                field_a = check["message_a"]["field"]
                msg_b_nid = check["message_b"]["nid_message"]
                field_b = check["message_b"]["field"]
                relation = check.get("relation", "equal")

                msgs_a = msgs_by_nid.get(msg_a_nid, [])
                msgs_b = msgs_by_nid.get(msg_b_nid, [])

                if msgs_a and msgs_b:
                    val_a = msgs_a[0].scenario_params.get(field_a)
                    val_b = msgs_b[0].scenario_params.get(field_b)

                    if val_a is not None and val_b is not None:
                        if relation == "equal" and val_a != val_b:
                            errors.append(ValidationError(
                                step=msgs_a[0].step,
                                message_name=msgs_a[0].name,
                                nid_message=msg_a_nid,
                                field=field_a,
                                error_code="CROSS_FIELD_MISMATCH",
                                description=(
                                    f"{rule['name']}: {rule['description']} — "
                                    f"msg {msg_a_nid}.{field_a}={val_a} != "
                                    f"msg {msg_b_nid}.{field_b}={val_b}"
                                ),
                                spec_ref="",
                            ))

        return ValidationResult(valid=len(errors) == 0, errors=errors)
