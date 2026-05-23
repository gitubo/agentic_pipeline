from abc import ABC, abstractmethod
from etcs_pipeline.config.settings import get_config, LLMProvider, GlobalConfig


class LLMClientBase(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        """Send a request to the model and return the response text."""
        ...


class AnthropicLLMClient(LLMClientBase):
    def __init__(self, cfg: GlobalConfig):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=cfg.anthropic_api_key)
        self._model = cfg.llm_model
        self._temperature = cfg.llm_temperature
        self._max_tokens_planner = cfg.llm_max_tokens_planner
        self._max_tokens_normalizer = cfg.llm_max_tokens_normalizer

    def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        from anthropic.types import TextBlock
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens or self._max_tokens_planner,
            temperature=self._temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        block = response.content[0]
        if isinstance(block, TextBlock):
            return block.text
        return str(block)


class OpenAILLMClient(LLMClientBase):
    """Covers both native OpenAI and any openai_compatible provider."""

    def __init__(self, cfg: GlobalConfig):
        from openai import OpenAI
        self._client = OpenAI(
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
        )
        self._model = cfg.llm_model
        self._temperature = cfg.llm_temperature
        self._max_tokens_planner = cfg.llm_max_tokens_planner
        self._max_tokens_normalizer = cfg.llm_max_tokens_normalizer

    def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=max_tokens or self._max_tokens_planner,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def build_llm_client(cfg: GlobalConfig | None = None) -> LLMClientBase:
    cfg = cfg or get_config()
    match cfg.llm_provider:
        case LLMProvider.ANTHROPIC:
            return AnthropicLLMClient(cfg)
        case LLMProvider.OPENAI | LLMProvider.OPENAI_COMPATIBLE:
            return OpenAILLMClient(cfg)
        case _:
            raise ValueError(f"Unsupported LLM provider: {cfg.llm_provider}")
