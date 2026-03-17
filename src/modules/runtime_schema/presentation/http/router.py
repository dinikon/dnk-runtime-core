from fastapi import APIRouter

router = APIRouter(prefix="/runtime-schema", tags=["runtime-schema"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "runtime_schema"}


__all__ = ["router"]
