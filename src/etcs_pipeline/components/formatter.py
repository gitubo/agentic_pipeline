from datetime import datetime, timezone
from etcs_pipeline.models.linked_list import LinkedList, MessageNode
from etcs_pipeline.models.validation import ValidationResult
from etcs_pipeline.models.output import (
    PipelineOutput, PipelineMetadata, OutputMessage, FieldValue,
    ValidationSummary
)
from etcs_pipeline.config.loader import ProfileLoader


class OutputFormatter:
    def __init__(self, loader: ProfileLoader):
        self._spec_version = loader.get_spec_version()
        self._profile_name = loader._profile.get("name", "")
        self._rules: dict[int, dict] = {}
        self._instantiator_fields: set[str] = set()
        try:
            rules = loader.load_rules()
            self._rules = {m["nid_message"]: m for m in rules.get("messages", [])}
        except Exception:
            pass
        try:
            self._instantiator_fields = loader.get_instantiator_field_names()
        except Exception:
            pass

    def format(
        self,
        ll: LinkedList,
        formal_result: ValidationResult | None,
        plausibility_result: ValidationResult | None,
        cache_hits: list[str],
        query: str,
    ) -> PipelineOutput:
        messages = [self._format_message(msg) for msg in ll.messages]
        requires_attention = sum(
            1 for msg in messages
            for fv in msg.fields.values()
            if fv.flag == "REQUIRES_EXPERT_INPUT"
        )
        formal_status = "PASSED" if (formal_result and formal_result.valid) else "FAILED"
        plaus_status = "PASSED"
        if plausibility_result:
            if not plausibility_result.valid:
                plaus_status = "FAILED"
            elif plausibility_result.warnings:
                plaus_status = "PASSED_WITH_WARNINGS"

        return PipelineOutput(
            status="SUCCESS",
            metadata=PipelineMetadata(
                scenario_description=query,
                spec_version=self._spec_version,
                generated_at=datetime.now(timezone.utc),
                rerun_count=0,
                cache_hits=cache_hits,
                profile=self._profile_name,
            ),
            messages=messages,
            validation_summary=ValidationSummary(
                formal_validation=formal_status,
                plausibility_check=plaus_status,
                warnings=[w.model_dump() for w in (
                    plausibility_result.warnings if plausibility_result else []
                )],
                requires_attention_count=requires_attention,
            ),
        )

    def format_failure(
        self,
        ll: LinkedList | None,
        formal_result: ValidationResult | None,
        plausibility_result: ValidationResult | None,
        query: str,
    ) -> PipelineOutput:
        residual: list[dict] = []
        if formal_result:
            residual.extend(e.model_dump() for e in formal_result.errors)
        if plausibility_result:
            residual.extend(e.model_dump() for e in plausibility_result.errors)

        return PipelineOutput(
            status="PIPELINE_FAILURE",
            metadata=PipelineMetadata(
                scenario_description=query,
                spec_version=self._spec_version,
                generated_at=datetime.now(timezone.utc),
                rerun_count=0,
                cache_hits=[],
                profile=self._profile_name,
            ),
            messages=[self._format_message(msg) for msg in ll.messages] if ll else [],
            validation_summary=ValidationSummary(
                formal_validation="FAILED",
                plausibility_check="FAILED",
                warnings=[],
                requires_attention_count=0,
            ),
            residual_errors=residual,
        )

    def _format_message(self, msg: MessageNode) -> OutputMessage:
        rule = self._rules.get(msg.nid_message, {})
        fields_map: dict[str, FieldValue] = {}

        for field, value in msg.scenario_params.items():
            if isinstance(value, dict) and value.get("flag") == "REQUIRES_EXPERT_INPUT":
                fv = FieldValue(
                    value=None,
                    source="requires_expert",
                    spec_ref=self._find_spec_ref(field, rule),
                    notes=value.get("note", ""),
                    flag="REQUIRES_EXPERT_INPUT",
                )
            else:
                fv = FieldValue(
                    value=value,
                    source="instantiator" if field in self._instantiator_fields else "scenario",
                    spec_ref=self._find_spec_ref(field, rule),
                )
            fields_map[field] = fv

        return OutputMessage(
            step=msg.step,
            nid_message=msg.nid_message,
            name=msg.name,
            direction=msg.direction.value,
            fields=fields_map,
            packets=[p.model_dump() for p in msg.packets],
            notes=msg.planner_notes,
        )

    def _find_spec_ref(self, field_name: str, rule: dict) -> str:
        for f in rule.get("required_fields", []) + rule.get("conditional_fields", []):
            if f.get("name") == field_name:
                return f.get("spec_ref", rule.get("spec_ref", ""))
        return rule.get("spec_ref", "")
