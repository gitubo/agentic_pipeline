import json
import re
from etcs_pipeline.models.linked_list import LinkedList
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.models.validation import ValidationResult
from etcs_pipeline.config.loader import ProfileLoader
from etcs_pipeline.config.llm_client import LLMClientBase
from etcs_pipeline.config.settings import get_config
from etcs_pipeline.cache.semantic_cache import SemanticCache
from etcs_pipeline.rag.retriever import RagRetriever


class LLMPlanner:
    def __init__(
        self,
        loader: ProfileLoader,
        cache: SemanticCache,
        rag: RagRetriever,
        llm: LLMClientBase,
    ):
        self._llm = llm
        self._max_tokens = get_config().llm_max_tokens_planner
        self._system_prompt = loader.load_prompt("planner_system")
        self._fewshot_template = loader.load_prompt("planner_fewshot")
        self._cache = cache
        self._rag = rag
        self._schema = loader.load_schema("linked_list")
        self._spec_version = loader.get_spec_version()

    def plan(
        self,
        features: ScenarioFeatures,
        previous_errors: ValidationResult | None = None,
        previous_linked_list: LinkedList | None = None,
    ) -> tuple[LinkedList, list[str]]:
        cache_hits, chain_examples = self._cache.retrieve(features)
        rag_context = self._rag.retrieve(features)

        if previous_errors is None:
            user_content = self._fewshot_template.format(
                scenario_features=features.model_dump_json(indent=2),
                chain_examples=json.dumps(chain_examples, indent=2, ensure_ascii=False),
                rag_context=rag_context,
                output_schema=json.dumps(self._schema, indent=2),
                spec_version=self._spec_version,
            )
        else:
            prev_ll_json = previous_linked_list.model_dump_json(indent=2) if previous_linked_list else "{}"
            user_content = (
                "The previous linked list produced validation errors.\n"
                "Surgically fix only the indicated nodes without modifying the rest.\n\n"
                f"PREVIOUS LINKED LIST:\n{prev_ll_json}\n\n"
                f"ERRORS TO FIX:\n{previous_errors.model_dump_json(indent=2)}\n\n"
                "Return the corrected linked list in the same JSON format."
            )

        raw = self._llm.complete(
            system=self._system_prompt,
            user=user_content,
            max_tokens=self._max_tokens,
        )
        json_str = self._extract_json(raw)
        return LinkedList.model_validate_json(json_str), cache_hits

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]
        raise ValueError(f"No JSON found in LLM response: {text[:200]}")
