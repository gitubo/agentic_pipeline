from etcs_pipeline.models.linked_list import LinkedList, MessageNode
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult, ValidationError, Severity
from etcs_pipeline.config.loader import ProfileLoader


class KinematicChecker:
    def __init__(self, loader: ProfileLoader):
        data = loader.load_kinematics()
        self._categories: dict[str, dict] = {
            c["id"]: c for c in data.get("categories", [])
        }
        self._checks: list[dict] = data.get("checks", [])
        self._checked_nids: set[int] = set(data.get("checked_nid_messages", []))
        self._spec_refs: dict[str, str] = {
            c["error_code"]: c.get("spec_ref", "")
            for c in self._checks
        }

    def check(self, ll: LinkedList, features: ScenarioFeatures) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        cat_id = features.train_category
        cat = self._categories.get(cat_id)
        if not cat:
            return ValidationResult(valid=True)

        for msg in ll.messages:
            if msg.nid_message in self._checked_nids:
                self._check_ma(msg, cat, features, errors, warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_ma(
        self,
        msg: MessageNode,
        cat: dict,
        features: ScenarioFeatures,
        errors: list,
        warnings: list,
    ) -> None:
        params = msg.scenario_params

        sections = params.get("sections", [])
        for sec in sections:
            v_static = sec.get("V_STATIC", 0) if isinstance(sec, dict) else 0
            if v_static > cat["max_speed_kmh"]:
                errors.append(ValidationError(
                    step=msg.step,
                    message_name=msg.name,
                    nid_message=msg.nid_message,
                    field="V_STATIC",
                    error_code="KINE_SPEED_EXCEEDS_CATEGORY_MAX",
                    description=(
                        f"V_STATIC={v_static} km/h exceeds the maximum for "
                        f"category {cat['id']} ({cat['max_speed_kmh']} km/h)"
                    ),
                    spec_ref=self._spec_refs.get("KINE_SPEED_EXCEEDS_CATEGORY_MAX", ""),
                    severity=Severity.ERROR,
                ))

        for sec in (sections if isinstance(sections, list) else []):
            if not isinstance(sec, dict):
                continue
            l_sec = sec.get("L_SECTION", 0)
            t_timer = sec.get("T_SECTIONTIMER")
            v_max_ms = (
                max(s.v_max_kmh for s in features.sections) / 3.6
                if features.sections else 200 / 3.6
            )
            if t_timer is not None and l_sec > 0 and v_max_ms > 0:
                min_time = (l_sec / v_max_ms) * cat["min_section_time_factor"]
                if t_timer < min_time:
                    errors.append(ValidationError(
                        step=msg.step,
                        message_name=msg.name,
                        nid_message=msg.nid_message,
                        field="T_SECTIONTIMER",
                        error_code="KINE_SECTION_TIMER_TOO_SHORT",
                        description=(
                            f"T_SECTIONTIMER={t_timer}s is too short for "
                            f"L_SECTION={l_sec}m at {v_max_ms * 3.6:.0f} km/h "
                            f"(minimum expected: {min_time:.1f}s)"
                        ),
                        spec_ref=self._spec_refs.get("KINE_SECTION_TIMER_TOO_SHORT", ""),
                        severity=Severity.ERROR,
                    ))

        v_release_raw = params.get("V_RELEASESPEED", features.v_release_kmh)
        v_release_ms = v_release_raw / 3.6
        d_ol = params.get("D_OL")
        if d_ol is not None:
            dec = cat["emergency_deceleration_ms2"]
            min_d_ol = (v_release_ms ** 2) / (2 * dec)
            if d_ol < min_d_ol:
                warnings.append(ValidationError(
                    step=msg.step,
                    message_name=msg.name,
                    nid_message=msg.nid_message,
                    field="D_OL",
                    error_code="KINE_OVERLAP_SHORT_FOR_RELEASE_SPEED",
                    description=(
                        f"D_OL={d_ol}m may be insufficient to brake from "
                        f"V_RELEASESPEED={v_release_ms * 3.6:.0f} km/h "
                        f"(estimated minimum distance: {min_d_ol:.0f}m)"
                    ),
                    spec_ref=self._spec_refs.get("KINE_OVERLAP_SHORT_FOR_RELEASE_SPEED", ""),
                    severity=Severity.WARNING,
                ))
