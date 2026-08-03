from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import ClientErrorEvent
from app.analytics.sanitizer import sanitize_client_error
from app.analytics.schemas import ClientErrorResponse
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.services.auth.dto import UserJWTData
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class RecordClientErrorCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    timestamp: datetime
    route: str
    release: str
    browser: str | None
    message: str
    stack: str | None
    component_stack: str | None
    request_id: str | None


@dataclass(frozen=True)
class RecordClientErrorHandler(BaseCommandHandler[RecordClientErrorCommand, ClientErrorResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: RecordClientErrorCommand) -> ClientErrorResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "organization:view")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="organization:view") from exc
        safe = sanitize_client_error(
            route=command.route,
            release=command.release,
            browser=command.browser,
            message=command.message,
            stack=command.stack,
            component_stack=command.component_stack,
            request_id=command.request_id,
        )
        stmt = (
            insert(ClientErrorEvent)
            .values(
                organization_id=command.organization_id,
                fingerprint=safe.fingerprint,
                route=safe.route,
                release=safe.release,
                browser=safe.browser,
                message=safe.message,
                stack=safe.stack,
                component_stack=safe.component_stack,
                request_id=safe.request_id,
                occurrences=1,
                first_seen_at=command.timestamp,
                last_seen_at=command.timestamp,
            )
            .on_conflict_do_update(
                index_elements=[
                    ClientErrorEvent.organization_id,
                    ClientErrorEvent.fingerprint,
                    ClientErrorEvent.release,
                ],
                set_={
                    "last_seen_at": command.timestamp,
                    "occurrences": ClientErrorEvent.occurrences + 1,
                    "browser": safe.browser,
                    "request_id": safe.request_id,
                },
            )
            .returning(
                ClientErrorEvent.id,
                ClientErrorEvent.fingerprint,
                ClientErrorEvent.occurrences,
                ClientErrorEvent.last_seen_at,
            )
        )
        row = (await self.session.execute(stmt)).one()
        await self.session.commit()
        return ClientErrorResponse(
            id=row.id,
            fingerprint=row.fingerprint,
            occurrences=row.occurrences,
            last_seen_at=row.last_seen_at,
        )
