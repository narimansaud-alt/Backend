import asyncio
import time
from contextlib import suppress

from dishka.integrations.taskiq import TaskiqProvider, setup_dishka
from redis.asyncio import Redis
from taskiq import ScheduleSource, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisScheduleSource

from app.core.configs.app import app_config
from app.core.di.container import create_container
from app.core.health import WORKER_HEARTBEAT_KEY, WORKER_HEARTBEAT_TTL_SECONDS
from app.core.message_brokers.base import BaseMessageBroker
from app.core.services.queues.taskiq.init import broker

container = create_container(TaskiqProvider())

setup_dishka(container=container, broker=broker)

worker_heartbeat_task: asyncio.Task[None] | None = None


async def worker_heartbeat(redis: Redis) -> None:
    while True:
        await redis.set(
            WORKER_HEARTBEAT_KEY,
            str(time.time()),
            ex=WORKER_HEARTBEAT_TTL_SECONDS,
        )
        await asyncio.sleep(WORKER_HEARTBEAT_TTL_SECONDS / 3)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    global worker_heartbeat_task  # noqa: PLW0603
    message_broker = await container.get(BaseMessageBroker)
    await message_broker.start()
    redis = await container.get(Redis)
    worker_heartbeat_task = asyncio.create_task(worker_heartbeat(redis), name="taskiq:worker-heartbeat")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState) -> None:
    global worker_heartbeat_task  # noqa: PLW0603
    if worker_heartbeat_task is not None:
        worker_heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_heartbeat_task
        worker_heartbeat_task = None
    message_broker = await container.get(BaseMessageBroker)
    await message_broker.close()


sources: list[ScheduleSource]

if app_config.ENVIRONMENT == "testing":
    sources = [LabelScheduleSource(broker=broker)]

else:
    redis_schedule_source = RedisScheduleSource(
        url=app_config.QUEUE_REDIS_BROKER_URL,
    )
    sources = [redis_schedule_source, LabelScheduleSource(broker=broker)]


scheduler = TaskiqScheduler(
    broker=broker,
    sources=sources,
)
