import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.services.auth.dto import UserJWTData
from app.core.utils import now_utc
from app.organizations.exceptions import (
    OrganizationForbiddenError,
    OrganizationNotFoundError,
    OwnerMutationError,
)
from app.organizations.models import (
    InvitationStatus,
    MemberCabinetAccess,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
)
from app.organizations.repositories import MemberRepository
from app.organizations.schemas import InvitationResponse, MemberResponse, OrganizationResponse
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class CreateOrganizationCommand(BaseCommand):
    user: UserJWTData
    name: str


@dataclass(frozen=True)
class CreateOrganizationHandler(BaseCommandHandler[CreateOrganizationCommand, OrganizationResponse]):
    session: AsyncSession

    async def handle(self, command: CreateOrganizationCommand) -> OrganizationResponse:
        user_id = int(command.user.id)
        organization = Organization(id=uuid4(), name=command.name.strip(), owner_user_id=user_id)
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user_id,
            role=OrganizationRole.OWNER,
        )
        self.session.add_all((organization, member))
        await self.session.commit()
        return OrganizationResponse.model_validate(organization)


@dataclass(frozen=True)
class InviteMemberCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    email: str
    role: OrganizationRole
    expires_in_hours: int


@dataclass(frozen=True)
class InviteMemberHandler(BaseCommandHandler[InviteMemberCommand, InvitationResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: InviteMemberCommand) -> InvitationResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "member:invite")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="member:invite") from exc
        if command.role is OrganizationRole.OWNER:
            raise OwnerMutationError
        token = secrets.token_urlsafe(32)
        invitation = OrganizationInvitation(
            organization_id=command.organization_id,
            email=command.email.lower(),
            role=command.role,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            invited_by_user_id=int(command.user.id),
            expires_at=now_utc() + timedelta(hours=command.expires_in_hours),
        )
        self.session.add(invitation)
        await self.session.commit()
        return InvitationResponse.model_validate(invitation, from_attributes=True).model_copy(
            update={"invite_token": token}
        )


@dataclass(frozen=True)
class AcceptInvitationCommand(BaseCommand):
    user: UserJWTData
    token: str


@dataclass(frozen=True)
class AcceptInvitationHandler(BaseCommandHandler[AcceptInvitationCommand, MemberResponse]):
    session: AsyncSession

    async def handle(self, command: AcceptInvitationCommand) -> MemberResponse:
        token_hash = hashlib.sha256(command.token.encode()).hexdigest()
        invitation = await self.session.scalar(
            select(OrganizationInvitation).where(
                OrganizationInvitation.token_hash == token_hash,
                OrganizationInvitation.status == InvitationStatus.PENDING,
            )
        )
        if invitation is None:
            raise OrganizationNotFoundError
        if invitation.expires_at <= now_utc():
            invitation.status = InvitationStatus.EXPIRED
            await self.session.commit()
            raise OrganizationNotFoundError
        user = await self.session.get(User, int(command.user.id))
        if user is None or user.email.casefold() != invitation.email.casefold():
            raise OrganizationNotFoundError
        member = await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == invitation.organization_id,
                OrganizationMember.user_id == user.id,
            )
        )
        if member is None:
            member = OrganizationMember(
                organization_id=invitation.organization_id,
                user_id=user.id,
                role=invitation.role,
            )
            self.session.add(member)
        else:
            member.is_active = True
        invitation.status = InvitationStatus.ACCEPTED
        await self.session.commit()
        return MemberResponse.model_validate(member)


@dataclass(frozen=True)
class UpdateMemberCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    member_id: UUID
    role: OrganizationRole
    cabinet_ids: frozenset[UUID]


@dataclass(frozen=True)
class UpdateMemberHandler(BaseCommandHandler[UpdateMemberCommand, MemberResponse]):
    session: AsyncSession
    member_repository: MemberRepository
    scope_service: OrganizationScopeService

    async def handle(self, command: UpdateMemberCommand) -> MemberResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "member:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="member:manage") from exc
        member = await self.member_repository.get(command.member_id, command.organization_id)
        if member is None:
            raise OrganizationNotFoundError
        if member.role == OrganizationRole.OWNER or command.role is OrganizationRole.OWNER:
            raise OwnerMutationError
        member.role = command.role
        await self.session.execute(delete(MemberCabinetAccess).where(MemberCabinetAccess.member_id == member.id))
        self.session.add_all(
            MemberCabinetAccess(member_id=member.id, cabinet_id=cabinet_id) for cabinet_id in command.cabinet_ids
        )
        await self.session.commit()
        return MemberResponse.model_validate(member)


@dataclass(frozen=True)
class RemoveMemberCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    member_id: UUID


@dataclass(frozen=True)
class RemoveMemberHandler(BaseCommandHandler[RemoveMemberCommand, None]):
    session: AsyncSession
    member_repository: MemberRepository
    scope_service: OrganizationScopeService

    async def handle(self, command: RemoveMemberCommand) -> None:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "member:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="member:manage") from exc
        member = await self.member_repository.get(command.member_id, command.organization_id)
        if member is None:
            raise OrganizationNotFoundError
        if member.role == OrganizationRole.OWNER:
            raise OwnerMutationError
        member.is_active = False
        await self.session.commit()
