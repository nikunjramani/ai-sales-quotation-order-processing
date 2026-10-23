"""Choose the enquiry interpreter by provider name. This is the only place providers are named.

Adding a provider (for example Claude or OpenAI) later:
1. `uv add --optional <name> langchain-<provider>`
2. Add "<name>" to Settings.model_provider and a branch below returning
   LangChainInterpreter(Chat<Provider>(model=model_name, temperature=0, ...)).
3. Put its API key in .env (never in code), then run scripts/evaluate_extraction.py.
Nothing else changes: the workflow only knows the EnquiryInterpreter contract.
"""

from quotation_app.adapters.interpreters.langchain import LangChainInterpreter
from quotation_app.adapters.interpreters.rules import RulesInterpreter
from quotation_app.ports.interpretation import EnquiryInterpreter


def build_interpreter(
    provider: str,
    model_name: str | None = None,
    ollama_base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: float = 120.0,
    api_key: str | None = None,
) -> EnquiryInterpreter:
    if provider == "rules":
        return RulesInterpreter()
    if provider == "ollama":
        if not model_name:
            raise ValueError("QUOTATION_MODEL_NAME is required for the ollama provider")
        # Imported here so the optional package is needed only when this provider is chosen.
        from langchain_ollama import ChatOllama

        model = ChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0,
            format="json",
            num_predict=2048,
            client_kwargs={"timeout": timeout_seconds},
        )
        return LangChainInterpreter(model)
    if provider == "gemini":
        if not model_name or not api_key:
            raise ValueError(
                "QUOTATION_MODEL_NAME and QUOTATION_GEMINI_API_KEY are required for gemini"
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Outages, rate limits and a bad key raise ordinary errors: the durable job retries
        # them with backoff (user decision: wait and retry, no fallback to rules).
        gemini = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            response_mime_type="application/json",
            timeout=timeout_seconds,
            max_retries=2,
        )
        return LangChainInterpreter(gemini)
    raise ValueError(f"Unknown model provider {provider!r}")
