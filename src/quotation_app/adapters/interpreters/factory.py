"""Choose the enquiry interpreter. Generic: no provider is named in code.

- No model configured: the free, offline rules interpreter.
- A model "<provider>:<model>" (e.g. "google_genai:gemini-3.5-flash-lite"): LangChain's
  init_chat_model builds that provider's chat model, wrapped in LangChainInterpreter.

Adding a provider (OpenAI, Claude, Groq, Ollama...): add its LangChain package to the "ai" extra
and set QUOTATION_MODEL / QUOTATION_MODEL_API_KEY in .env, then run
scripts/evaluate_extraction.py. Nothing else changes.
"""

from collections.abc import Mapping
from typing import Any

from quotation_app.adapters.interpreters.langchain import LangChainInterpreter
from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.ports.interpretation import EnquiryInterpreter


def build_interpreter(
    model: str | None = None,
    api_key: str | None = None,
    options: Mapping[str, Any] | None = None,
) -> EnquiryInterpreter:
    if not model:
        return RulesInterpreter()
    provider, separator, name = model.partition(":")
    if not separator or not provider or not name:
        raise ValueError("The model must look like '<provider>:<model>'")
    # Imported here so the optional "ai" packages are needed only when a model is configured.
    from langchain.chat_models import init_chat_model

    settings: dict[str, Any] = {"temperature": 0, **(options or {})}
    if api_key:
        settings["api_key"] = api_key
    try:
        chat = init_chat_model(name, model_provider=provider, **settings)
    except ImportError as error:
        raise ValueError(
            f"The LangChain package for provider {provider!r} is not installed: {error}"
        ) from None
    # Outages, rate limits and a bad key raise ordinary errors at call time: the durable job
    # retries them with backoff (user decision: wait and retry, no fallback to rules).
    return LangChainInterpreter(chat)
