import pytest
from pydantic import SecretStr

from quotation_app.config import Settings
from quotation_app.persistence.seed import seed_demo_tenants


def test_production_seed_is_rejected_before_connecting() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url=SecretStr("postgresql+psycopg://app:private@localhost/db"),
    )
    with pytest.raises(ValueError, match="disabled"):
        seed_demo_tenants(settings)
