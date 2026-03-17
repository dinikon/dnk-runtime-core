from fastapi import APIRouter

router = APIRouter(prefix="/runtime-record", tags=["runtime-record"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "runtime_record"}


__all__ = ["router"]
