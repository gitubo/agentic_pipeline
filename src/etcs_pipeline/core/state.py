from typing import TypedDict
from etcs_pipeline.models.linked_list import LinkedList
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult
from etcs_pipeline.models.output import PipelineOutput


class PipelineState(TypedDict):
    # Input
    query: str
    profile_name: str

    # Prodotto dal Normalizer
    features: ScenarioFeatures | None

    # Prodotto dalla Cache
    cache_hits: list[str]
    chain_examples: list[dict]

    # Prodotto dal Planner (aggiornato a ogni rerun)
    linked_list: LinkedList | None

    # Risultati validazione
    formal_validation: ValidationResult | None
    plausibility_result: ValidationResult | None

    # Contatori rerun
    formal_rerun_count: int
    plausibility_rerun_count: int

    # Output finale
    output: PipelineOutput | None
    error: dict | None
