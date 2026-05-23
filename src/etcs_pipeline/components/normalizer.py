import re
from etcs_pipeline.models.scenario import ScenarioFeatures
from etcs_pipeline.config.loader import ProfileLoader
from etcs_pipeline.config.llm_client import LLMClientBase
from etcs_pipeline.config.settings import get_config


class QueryNormalizer:
    def __init__(self, loader: ProfileLoader, llm: LLMClientBase):
        self._llm = llm
        self._system_prompt = loader.load_prompt("normalizer")
        self._schema = loader.load_schema("scenario_features")
        self._max_tokens = get_config().llm_max_tokens_normalizer

    def normalize(self, query: str) -> ScenarioFeatures:
        raw = self._llm.complete(
            system=self._system_prompt,
            user=f"Scenario: {query}\n\nReply with valid JSON according to the schema.",
            max_tokens=self._max_tokens,
        )
        json_str = self._extract_json(raw)
        return ScenarioFeatures.model_validate_json(json_str)

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]
        raise ValueError(f"No JSON found in LLM response: {text[:200]}")
