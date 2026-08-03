import time

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.schemas import ORJSONResponse
from app.core.health import WORKER_HEARTBEAT_KEY, WORKER_HEARTBEAT_TTL_SECONDS

router = APIRouter(tags=["core"], route_class=DishkaRoute)


@router.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck() -> ORJSONResponse:
    return ORJSONResponse("Ok")


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(
    session: FromDishka[AsyncSession],
    redis: FromDishka[Redis],
) -> ORJSONResponse:
    """Verify the stateful dependencies required to serve API requests."""
    checks: dict[str, str] = {"api": "ok"}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 -- readiness must convert dependency errors to 503
        checks["database"] = "unavailable"

    try:
        redis_available = bool(await redis.ping())
        checks["redis"] = "ok" if redis_available else "unavailable"
        heartbeat = await redis.get(WORKER_HEARTBEAT_KEY) if redis_available else None
        heartbeat_age = time.time() - float(heartbeat) if heartbeat is not None else float("inf")
        checks["worker"] = "ok" if heartbeat_age <= WORKER_HEARTBEAT_TTL_SECONDS else "unavailable"
    except Exception:  # noqa: BLE001 -- readiness must convert dependency errors to 503
        checks["redis"] = "unavailable"
        checks["worker"] = "unavailable"

    ready = all(value == "ok" for value in checks.values())
    return ORJSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
