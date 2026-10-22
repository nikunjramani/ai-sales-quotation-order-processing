"""Our frozen copy of LangGraph's checkpoint schema must match the installed library.

If this fails after upgrading langgraph-checkpoint-postgres, add a new Alembic migration with
the library's new statements (do not edit migration 0004).
"""

import importlib.util
from pathlib import Path

from langgraph.checkpoint.postgres.base import BasePostgresSaver

MIGRATION = Path(__file__).resolve().parents[3] / "migrations" / "versions" / "0004_workflow.py"


def _normalise(statement: str) -> str:
    return " ".join(statement.split())


def test_frozen_checkpoint_migrations_match_library() -> None:
    spec = importlib.util.spec_from_file_location("migration_0004", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frozen = [_normalise(statement) for statement in module.LANGGRAPH_CHECKPOINT_MIGRATIONS]
    library = [_normalise(statement) for statement in BasePostgresSaver.MIGRATIONS]
    assert frozen == library
