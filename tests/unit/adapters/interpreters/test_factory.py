import pytest

from quotation_app.adapters.interpreters.factory import build_interpreter
from quotation_app.adapters.interpreters.langchain import LangChainInterpreter
from quotation_app.adapters.interpreters.rules import RulesInterpreter


def test_rules_is_the_free_default() -> None:
    assert isinstance(build_interpreter("rules"), RulesInterpreter)


def test_ollama_builds_without_contacting_the_server() -> None:
    assert isinstance(build_interpreter("ollama", "any-local-model"), LangChainInterpreter)
    with pytest.raises(ValueError, match="MODEL_NAME"):
        build_interpreter("ollama")


def test_gemini_builds_without_contacting_google() -> None:
    interpreter = build_interpreter("gemini", "gemini-3.5-flash-lite", api_key="synthetic-test-key")
    assert isinstance(interpreter, LangChainInterpreter)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_interpreter("gemini", "gemini-3.5-flash-lite")
    with pytest.raises(ValueError, match="MODEL_NAME"):
        build_interpreter("gemini", api_key="synthetic-test-key")


def test_unknown_provider_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown model provider"):
        build_interpreter("magic")
