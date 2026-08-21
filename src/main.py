from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.integration.health_route import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="har-provider-lookup")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router)
    return app


app = create_app()
