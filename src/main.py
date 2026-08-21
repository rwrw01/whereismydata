from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.integration.health_route import router as health_router
from src.integration.lookup_route import router as lookup_router
from src.service.cache import TTLCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    app.state.cache = TTLCache(redis_url=settings.redis_url)
    yield
    await app.state.http_client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="har-provider-lookup", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router)
    app.include_router(lookup_router)
    return app


app = create_app()
