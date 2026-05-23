import traceback
from datetime import datetime, timezone
from langgraph.graph.graph import CompiledGraph
from etcs_pipeline.core.graph import build_graph
from etcs_pipeline.core.state import PipelineState
from etcs_pipeline.models.output import (
    PipelineOutput, PipelineMetadata, ValidationSummary
)


class PipelineRunner:

    def __init__(self, profile_name: str | None = None):
        if profile_name is None:
            from etcs_pipeline.config.settings import get_config
            profile_name = get_config().active_profile
        self._graph: CompiledGraph = build_graph(profile_name)
        self._profile_name = profile_name

    def run(self, query: str) -> PipelineOutput:
        initial_state: PipelineState = {
            "query": query,
            "profile_name": self._profile_name,
            "features": None,
            "cache_hits": [],
            "chain_examples": [],
            "linked_list": None,
            "formal_validation": None,
            "plausibility_result": None,
            "formal_rerun_count": 0,
            "plausibility_rerun_count": 0,
            "output": None,
            "error": None,
        }
        try:
            final_state = self._graph.invoke(initial_state)
            return final_state["output"]
        except Exception as exc:
            return PipelineOutput(
                status="INFRASTRUCTURE_FAILURE",
                metadata=PipelineMetadata(
                    scenario_description=query,
                    spec_version="unknown",
                    generated_at=datetime.now(timezone.utc),
                    rerun_count=0,
                    cache_hits=[],
                    profile=self._profile_name,
                ),
                messages=[],
                validation_summary=ValidationSummary(
                    formal_validation="NOT_RUN",
                    plausibility_check="NOT_RUN",
                    warnings=[],
                    requires_attention_count=0,
                ),
                residual_errors=[{
                    "type": "INFRASTRUCTURE_FAILURE",
                    "detail": str(exc),
                    "traceback": traceback.format_exc(),
                }],
            )
