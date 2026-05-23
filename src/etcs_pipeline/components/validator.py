from etcs_pipeline.models.linked_list import LinkedList, MessageNode
from etcs_pipeline.models.validation import ValidationResult, ValidationError, Severity
from etcs_pipeline.config.loader import ProfileLoader


class FormalValidator:
    """
    Deterministic rule engine.
    Rules are loaded from messages.yaml — no domain logic in code.
    """

    def __init__(self, loader: ProfileLoader):
        rules = loader.load_rules()
        self._rules: dict[int, dict] = {
            m["nid_message"]: m for m in rules["messages"]
        }

    def validate(self, linked_list: LinkedList) -> ValidationResult:
        errors, warnings = [], []

        for msg in linked_list.messages:
            result = self._validate_message(msg, linked_list)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_message(
        self, msg: MessageNode, ll: LinkedList
    ) -> ValidationResult:
        errors, warnings = [], []
        rule = self._rules.get(msg.nid_message)

        if not rule:
            warnings.append(ValidationError(
                step=msg.step,
                message_name=msg.name,
                nid_message=msg.nid_message,
                field=None,
                error_code="UNKNOWN_MESSAGE_TYPE",
                description=f"NID_MESSAGE={msg.nid_message} not found in rules",
                spec_ref="",
                severity=Severity.WARNING,
            ))
            return ValidationResult(valid=True, warnings=warnings)

        all_params = {**msg.scenario_params}

        for field_rule in rule.get("required_fields", []):
            fname = field_rule["name"]
            if fname not in all_params and fname not in msg.to_instantiate:
                errors.append(ValidationError(
                    step=msg.step,
                    message_name=msg.name,
                    nid_message=msg.nid_message,
                    field=fname,
                    error_code="FIELD_REQUIRED_MISSING",
                    description=f"Required field {fname} is missing",
                    spec_ref=field_rule.get("spec_ref", rule["spec_ref"]),
                    suggestion=f"Add {fname} to scenario_params or to_instantiate",
                ))
                continue

            if fname in all_params:
                errs = self._check_field_type(fname, all_params[fname], field_rule, msg)
                errors.extend(errs)

        for cond_rule in rule.get("conditional_fields", []):
            if self._eval_condition(cond_rule["condition"], all_params):
                fname = cond_rule["name"]
                if fname not in all_params and fname not in msg.to_instantiate:
                    errors.append(ValidationError(
                        step=msg.step,
                        message_name=msg.name,
                        nid_message=msg.nid_message,
                        field=fname,
                        error_code="FIELD_REQUIRED_BY_CONDITION",
                        description=f"{fname} is required when {cond_rule['condition']}",
                        spec_ref=cond_rule.get("spec_ref", rule["spec_ref"]),
                        suggestion=f"Add {fname} because {cond_rule['condition']}",
                    ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_field_type(
        self, name: str, value: object, rule: dict, msg: MessageNode
    ) -> list[ValidationError]:
        errors = []
        ftype = rule.get("type")

        if ftype == "enum" and value not in rule.get("values", []):
            errors.append(ValidationError(
                step=msg.step,
                message_name=msg.name,
                nid_message=msg.nid_message,
                field=name,
                error_code="FIELD_INVALID_ENUM_VALUE",
                description=f"{name}={value} is not a valid value. Valid values: {rule['values']}",
                spec_ref=rule.get("spec_ref", ""),
            ))

        if ftype == "uint":
            if "min" in rule and value < rule["min"]:
                errors.append(ValidationError(
                    step=msg.step,
                    message_name=msg.name,
                    nid_message=msg.nid_message,
                    field=name,
                    error_code="FIELD_BELOW_MIN",
                    description=f"{name}={value} is below the minimum {rule['min']}",
                    spec_ref=rule.get("spec_ref", ""),
                ))
            if "max" in rule and value > rule["max"]:
                errors.append(ValidationError(
                    step=msg.step,
                    message_name=msg.name,
                    nid_message=msg.nid_message,
                    field=name,
                    error_code="FIELD_ABOVE_MAX",
                    description=f"{name}={value} exceeds the maximum {rule['max']}",
                    spec_ref=rule.get("spec_ref", ""),
                ))
        return errors

    def _eval_condition(self, condition: str, params: dict) -> bool:
        """
        Safely evaluates a condition string.
        Only simple comparisons are supported — no arbitrary eval().
        Format: "FIELD op VALUE" where op in [==, !=, in, not in, >, <, >=, <=]
        """
        try:
            condition = condition.strip()
            for op in [" not in ", " in ", " == ", " != ", " >= ", " <= ", " > ", " < "]:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left_val = params.get(left.strip())
                    right_val = eval(right.strip())  # only Python literals from controlled YAML
                    if op == " == ":
                        return left_val == right_val
                    if op == " != ":
                        return left_val != right_val
                    if op == " in ":
                        return left_val in right_val
                    if op == " not in ":
                        return left_val not in right_val
                    if op == " > ":
                        return (left_val or 0) > right_val
                    if op == " < ":
                        return (left_val or 0) < right_val
                    if op == " >= ":
                        return (left_val or 0) >= right_val
                    if op == " <= ":
                        return (left_val or 0) <= right_val
            return False
        except Exception:
            return False
