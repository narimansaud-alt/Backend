import csv
import logging
from dataclasses import dataclass
from io import BytesIO, StringIO
from uuid import UUID, uuid4
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import AnalyticsDaily, ExportJob
from app.analytics.schemas import AnalyticsFilters, ExportJobResponse
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.core.services.queues.service import QueueService
from app.core.services.queues.task import BaseTask
from app.core.services.storage.dtos import UploadFile
from app.core.services.storage.service import StorageService
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.services import OrganizationScopeService

logger = logging.getLogger(__name__)
EXPORT_BUCKET = "base"


def _table(rows: list[AnalyticsDaily]) -> tuple[list[str], list[list[str]]]:
    metric_codes = sorted({code for row in rows for code in row.metrics})
    headers = ["business_date", "cabinet_id", "product_id", *metric_codes]
    values = [
        [
            row.business_date.isoformat(),
            str(row.cabinet_id),
            str(row.product_id or ""),
            *[str(row.metrics.get(code) if row.metrics.get(code) is not None else "") for code in metric_codes],
        ]
        for row in rows
    ]
    return headers, values


def _safe_csv_cell(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def _csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows([[_safe_csv_cell(value) for value in row] for row in rows])
    return stream.getvalue().encode("utf-8-sig")


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    sheet_rows: list[str] = []
    for row_index, row in enumerate([headers, *rows], start=1):
        cells = "".join(
            f'<c r="{_column_name(column_index)}{row_index}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            for column_index, value in enumerate(row, start=1)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Analytics" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


@dataclass
class ExportRunner:
    session: AsyncSession
    storage: StorageService

    async def run(self, export_id: str) -> None:
        job = await self.session.get(ExportJob, UUID(export_id))
        if job is None or job.status != "queued":
            return
        job.status = "running"
        await self.session.commit()
        try:
            filters = AnalyticsFilters.model_validate(job.filters)
            statement = select(AnalyticsDaily).where(
                AnalyticsDaily.organization_id == job.organization_id,
                AnalyticsDaily.business_date.between(filters.date_from, filters.date_to),
            )
            if filters.cabinet_ids:
                statement = statement.where(AnalyticsDaily.cabinet_id.in_(filters.cabinet_ids))
            rows = list(
                (
                    await self.session.scalars(
                        statement.order_by(AnalyticsDaily.business_date, AnalyticsDaily.cabinet_id)
                    )
                ).all()
            )
            headers, values = _table(rows)
            content = _csv_bytes(headers, values) if job.format == "csv" else _xlsx_bytes(headers, values)
            content_type = (
                "text/csv; charset=utf-8"
                if job.format == "csv"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            storage_key = f"exports/{job.organization_id}/{job.id}.{job.format}"
            await self.storage.upload_file(
                UploadFile(
                    bucket_name=EXPORT_BUCKET,
                    file_content=BytesIO(content),
                    file_key=storage_key,
                    size=len(content),
                    content_type=content_type,
                    metadata={"organization_id": str(job.organization_id), "export_id": str(job.id)},
                )
            )
            job.storage_key = storage_key
            job.status = "succeeded"
            job.error_code = None
            await self.session.commit()
        except Exception:  # noqa: BLE001 -- persist a terminal job state before Taskiq records failure
            await self.session.rollback()
            failed = await self.session.get(ExportJob, UUID(export_id))
            if failed is not None:
                failed.status = "failed"
                failed.error_code = "EXPORT_FAILED"
                await self.session.commit()
            logger.exception("Export generation failed", extra={"export_id": export_id})
            raise


@dataclass
class GenerateExportTask(BaseTask):
    __task_name__ = "analytics.export"

    @staticmethod
    @inject
    async def run(export_id: str, runner: FromDishka[ExportRunner]) -> None:
        await runner.run(export_id)


@dataclass(frozen=True)
class CreateExportCommand(BaseCommand):
    user: UserJWTData
    filters: AnalyticsFilters
    format: str


@dataclass(frozen=True)
class CreateExportHandler(BaseCommandHandler[CreateExportCommand, ExportJobResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService
    queue: QueueService

    async def handle(self, command: CreateExportCommand) -> ExportJobResponse:
        try:
            scope = await self.scope_service.require(
                int(command.user.id), command.filters.organization_id, "analytics:export"
            )
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="analytics:export") from exc
        allowed = scope.restrict_cabinets(set(command.filters.cabinet_ids) or None)
        if allowed is not None and not allowed:
            raise OrganizationForbiddenError(permission="analytics:export")
        export_filters = command.filters.model_copy(update={"cabinet_ids": set(allowed or [])})
        job = ExportJob(
            id=uuid4(),
            organization_id=command.filters.organization_id,
            requested_by_user_id=int(command.user.id),
            status="queued",
            format=command.format,
            filters=export_filters.model_dump(mode="json"),
        )
        self.session.add(job)
        await self.session.commit()
        await self.queue.push(GenerateExportTask, {"export_id": str(job.id)})
        return ExportJobResponse.model_validate(job)


@dataclass(frozen=True)
class GetExportQuery(BaseQuery):
    user: UserJWTData
    export_id: UUID


@dataclass(frozen=True)
class GetExportHandler(BaseQueryHandler[GetExportQuery, ExportJobResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService
    storage: StorageService

    async def handle(self, query: GetExportQuery) -> ExportJobResponse:
        job = await self.session.get(ExportJob, query.export_id)
        if job is None:
            raise OrganizationForbiddenError(permission="analytics:export")
        try:
            await self.scope_service.require(int(query.user.id), job.organization_id, "analytics:export")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="analytics:export") from exc
        download_url = None
        if job.status == "succeeded" and job.storage_key:
            download_url = await self.storage.generate_presigned_url(EXPORT_BUCKET, job.storage_key, expires=900)
        return ExportJobResponse.model_validate(job).model_copy(update={"download_url": download_url})
