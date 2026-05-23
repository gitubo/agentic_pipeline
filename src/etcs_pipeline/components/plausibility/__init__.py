from typing import Union
from etcs_pipeline.models.linked_list import LinkedList
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult, ValidationError
from etcs_pipeline.config.loader import ProfileLoader
from .state_machine import StateMachineValidator
from .cross_message import CrossMessageChecker
from .kinematics import KinematicChecker

_CheckerType = Union[StateMachineValidator, CrossMessageChecker, KinematicChecker]


class PlausibilityChecker:
    def __init__(self, loader: ProfileLoader):
        self._state_machine = StateMachineValidator(loader)
        self._cross_message = CrossMessageChecker(loader)
        self._kinematics = KinematicChecker(loader)

    def check(
        self, linked_list: LinkedList, features: ScenarioFeatures
    ) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        checkers: list[_CheckerType] = [
            self._state_machine, self._cross_message, self._kinematics
        ]
        for checker in checkers:
            result = checker.check(linked_list, features)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
