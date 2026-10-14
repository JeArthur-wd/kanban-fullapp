from fastapi import APIRouter

from app.routes import auth, board, chat, health, static

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(board.router)
api_router.include_router(chat.router)

# The catch-all static route must be registered after every API route.
static_router = static.router
