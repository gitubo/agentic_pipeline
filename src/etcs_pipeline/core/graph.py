from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph
from etcs_pipeline.core.state import PipelineState
from etcs_pipeline.components.normalizer import QueryNormalizer
from etcs_pipeline.components.planner import LLMPlanner
from etcs_pipeline.components.validator import FormalValidator
from etcs_pipeline.components.plausibility import PlausibilityChecker
from etcs_pipeline.components.instantiator import Instantiator
from etcs_pipeline.components.formatter import OutputFormatter
from etcs_pipeline.config.loader import ProfileLoader
from etcs_pipeline.config.llm_client import build_llm_client
from etcs_pipeline.config.settings import get_config
from etcs_pipeline.cache.semantic_cache import SemanticCache
from etcs_pipeline.rag.retriever import RagRetriever


def build_graph(profile_name: str | None = None) -> CompiledGraph:
    cfg = get_config()
    loader = ProfileLoader(profile_name)
    cache = SemanticCache(loader)
    rag = RagRetriever(loader)

    llm_client = build_llm_client()
    normalizer = QueryNormalizer(loader, llm=llm_client)
    planner = LLMPlanner(loader, cache, rag, llm=llm_client)
    validator = FormalValidator(loader)
    plausibility = PlausibilityChecker(loader)
    instantiator = Instantiator(loader)
    formatter = OutputFormatter(loader)

    max_formal_rerun = cfg.max_rerun_formal_validator
    max_plaus_rerun = cfg.max_rerun_plausibility

    # ── Nodi ──────────────────────────────────────────────────────────────

    def normalize(state: PipelineState) -> PipelineState:
        features = normalizer.normalize(state["query"])
        if features.requires_clarification:
            return {**state, "error": {
                "type": "REQUIRES_CLARIFICATION",
                "missing": features.requires_clarification,
            }}
        return {**state, "features": features}

    def plan(state: PipelineState) -> PipelineState:
        features = state["features"]
        assert features is not None
        ll, hits = planner.plan(
            features,
            previous_errors=state.get("formal_validation")
            if state.get("formal_rerun_count", 0) > 0 else None,
            previous_linked_list=state.get("linked_list"),
        )
        return {**state, "linked_list": ll, "cache_hits": hits}

    def validate_formal(state: PipelineState) -> PipelineState:
        ll = state["linked_list"]
        assert ll is not None
        result = validator.validate(ll)
        return {**state, "formal_validation": result}

    def check_plausibility(state: PipelineState) -> PipelineState:
        ll = state["linked_list"]
        features = state["features"]
        assert ll is not None and features is not None
        result = plausibility.check(ll, features)
        return {**state, "plausibility_result": result}

    def instantiate(state: PipelineState) -> PipelineState:
        ll = state["linked_list"]
        assert ll is not None
        ll = instantiator.complete(ll)
        return {**state, "linked_list": ll}

    def format_output(state: PipelineState) -> PipelineState:
        ll = state["linked_list"]
        assert ll is not None
        output = formatter.format(
            ll,
            state["formal_validation"],
            state["plausibility_result"],
            state["cache_hits"],
            state["query"],
        )
        return {**state, "output": output}

    def handle_failure(state: PipelineState) -> PipelineState:
        output = formatter.format_failure(
            state.get("linked_list"),
            state.get("formal_validation"),
            state.get("plausibility_result"),
            state["query"],
        )
        return {**state, "output": output}

    def increment_formal_rerun(state: PipelineState) -> PipelineState:
        return {**state, "formal_rerun_count": state.get("formal_rerun_count", 0) + 1}

    def increment_plaus_rerun(state: PipelineState) -> PipelineState:
        return {**state, "plausibility_rerun_count": state.get("plausibility_rerun_count", 0) + 1}

    # ── Routing ───────────────────────────────────────────────────────────

    def route_after_normalize(state: PipelineState) -> str:
        if state.get("error"):
            return "failure"
        return "plan"

    def route_after_formal_validation(state: PipelineState) -> str:
        result = state["formal_validation"]
        assert result is not None
        if result.valid:
            return "check_plausibility"
        count = state.get("formal_rerun_count", 0)
        if count < max_formal_rerun:
            return "replan_formal"
        return "failure"

    def route_after_plausibility(state: PipelineState) -> str:
        result = state["plausibility_result"]
        assert result is not None
        if result.valid:
            return "instantiate"
        count = state.get("plausibility_rerun_count", 0)
        if count < max_plaus_rerun:
            return "replan_plausibility"
        return "failure"

    # ── Costruzione grafo ─────────────────────────────────────────────────

    builder = StateGraph(PipelineState)

    builder.add_node("normalize", normalize)
    builder.add_node("plan", plan)
    builder.add_node("validate_formal", validate_formal)
    builder.add_node("increment_formal_rerun", increment_formal_rerun)
    builder.add_node("check_plausibility", check_plausibility)
    builder.add_node("increment_plaus_rerun", increment_plaus_rerun)
    builder.add_node("instantiate", instantiate)
    builder.add_node("format_output", format_output)
    builder.add_node("failure", handle_failure)

    builder.set_entry_point("normalize")
    builder.add_conditional_edges("normalize", route_after_normalize, {
        "plan": "plan",
        "failure": "failure",
    })
    builder.add_edge("plan", "validate_formal")
    builder.add_conditional_edges("validate_formal", route_after_formal_validation, {
        "check_plausibility": "check_plausibility",
        "replan_formal": "increment_formal_rerun",
        "failure": "failure",
    })
    builder.add_edge("increment_formal_rerun", "plan")
    builder.add_conditional_edges("check_plausibility", route_after_plausibility, {
        "instantiate": "instantiate",
        "replan_plausibility": "increment_plaus_rerun",
        "failure": "failure",
    })
    builder.add_edge("increment_plaus_rerun", "plan")
    builder.add_edge("instantiate", "format_output")
    builder.add_edge("format_output", END)
    builder.add_edge("failure", END)

    return builder.compile()
