from fastapi import APIRouter

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "crm"}


__all__ = ["router"]
