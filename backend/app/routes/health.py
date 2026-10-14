from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@router.get("/api/hello")
def hello() -> dict:
    return {"message": "Hello from FastAPI"}
