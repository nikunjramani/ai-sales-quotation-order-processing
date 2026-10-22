"""Application factory. Startup does not mutate or migrate the database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from quotation_app.adapters.storage.local import LocalObjectStorage
from quotation_app.api.enquiries import build_enquiry_router
from quotation_app.application.api_keys import ApiKeyAuthenticator
from quotation_app.application.intake import EnquiryIntakeService
from quotation_app.config import Settings
from quotation_app.persistence.api_keys import SqlApiKeyReader
from quotation_app.persistence.database import build_engine, database_ready
from quotation_app.persistence.intake import SqlIntakeStore


class HealthResponse(BaseModel):
    status: Literal["ok", "ready", "not_ready"]


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()
    engine = build_engine(configuration.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Sales Quotation Automation", version="0.1.0", lifespan=lifespan)

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    def live() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
        tags=["health"],
    )
    def ready(response: Response) -> HealthResponse:
        try:
            available = database_ready(engine)
        except SQLAlchemyError:
            available = False
        if not available:
            response.status_code = 503
        return HealthResponse(status="ready" if available else "not_ready")

    # Composition root: wire adapters to application services. Nothing connects until used.
    intake = EnquiryIntakeService(
        SqlIntakeStore(engine), LocalObjectStorage(configuration.storage_dir)
    )
    app.include_router(build_enquiry_router(ApiKeyAuthenticator(SqlApiKeyReader(engine)), intake))
    return app
