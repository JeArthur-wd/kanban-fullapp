from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import api_router, static_router
from app.routes.static import get_static_dir, mount_static_assets


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    static_dir = get_static_dir()
    if static_dir:
        mount_static_assets(app, static_dir)
    app.include_router(api_router)
    app.include_router(static_router)
    return app


app = create_app()
