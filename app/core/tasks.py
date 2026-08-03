from taskiq import AsyncBroker

from app.analytics.exports import GenerateExportTask
from app.auth.tasks import register_auth_tasks
from app.core.services.mail.aiosmtplib.task import SendEmail
from app.marketplaces.tasks import RunSyncJobTask


def register_tasks(broker: AsyncBroker) -> None:
    broker.register_task(SendEmail.run, task_name=SendEmail.get_name())

    register_auth_tasks(broker)
    broker.register_task(RunSyncJobTask.run, task_name=RunSyncJobTask.get_name())
    broker.register_task(GenerateExportTask.run, task_name=GenerateExportTask.get_name())
