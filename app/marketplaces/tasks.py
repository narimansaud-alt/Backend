from dataclasses import dataclass

from dishka import FromDishka
from dishka.integrations.taskiq import inject

from app.core.services.queues.task import BaseTask
from app.marketplaces.sync import SyncJobRunner


@dataclass
class RunSyncJobTask(BaseTask):
    __task_name__ = "marketplaces.sync_job"

    @staticmethod
    @inject
    async def run(job_id: str, runner: FromDishka[SyncJobRunner]) -> None:
        await runner.run(job_id)
