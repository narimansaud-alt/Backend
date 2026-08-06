import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import DuplicateUserError, NotFoundRoleError, PasswordMismatchError
from app.auth.models.role_permission import RolesEnum
from app.auth.models.user import User
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.user import UserRepository
from app.auth.services.hash import HashService
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.services.auth.dto import UserJWTData
from app.core.utils import now_utc
from app.organizations.exceptions import (
    MemberAlreadyExistsError,
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
from app.organizations.schemas import (
    InvitationRegistrationResponse,
    InvitationResponse,
    MemberResponse,
    OrganizationResponse,
)
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
class UpdateOrganizationCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    name: str | None
    is_active: bool | None


@dataclass(frozen=True)
class UpdateOrganizationHandler(BaseCommandHandler[UpdateOrganizationCommand, OrganizationResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: UpdateOrganizationCommand) -> OrganizationResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "organization:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="organization:manage") from exc
        organization = await self.session.get(Organization, command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError
        if command.name is not None:
            organization.name = command.name.strip()
        if command.is_active is not None:
            organization.is_active = command.is_active
        await self.session.commit()
        return OrganizationResponse.model_validate(organization)


@dataclass(frozen=True)
class DeleteOrganizationCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID


@dataclass(frozen=True)
class DeleteOrganizationHandler(BaseCommandHandler[DeleteOrganizationCommand, None]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: DeleteOrganizationCommand) -> None:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "organization:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="organization:manage") from exc
        organization = await self.session.get(Organization, command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError
        organization.is_active = False
        await self.session.commit()


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
        normalized_email = command.email.strip().casefold()
        existing_member = await self.session.scalar(
            select(OrganizationMember)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == command.organization_id,
                OrganizationMember.is_active.is_(True),
                User.email == normalized_email,
            )
        )
        if existing_member is not None:
            raise MemberAlreadyExistsError
        await self.session.execute(
            update(OrganizationInvitation)
            .where(
                OrganizationInvitation.organization_id == command.organization_id,
                OrganizationInvitation.email == normalized_email,
                OrganizationInvitation.status == InvitationStatus.PENDING,
            )
            .values(status=InvitationStatus.REVOKED)
        )
        token = secrets.token_urlsafe(32)
        invitation = OrganizationInvitation(
            organization_id=command.organization_id,
            email=normalized_email,
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


async def _get_pending_invitation(session: AsyncSession, token: str) -> OrganizationInvitation:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation = await session.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == token_hash,
            OrganizationInvitation.status == InvitationStatus.PENDING,
        )
    )
    if invitation is None:
        raise OrganizationNotFoundError
    if invitation.expires_at <= now_utc():
        invitation.status = InvitationStatus.EXPIRED
        await session.commit()
        raise OrganizationNotFoundError
    return invitation


@dataclass(frozen=True)
class AcceptInvitationCommand(BaseCommand):
    user: UserJWTData
    token: str


@dataclass(frozen=True)
class AcceptInvitationHandler(BaseCommandHandler[AcceptInvitationCommand, MemberResponse]):
    session: AsyncSession

    async def handle(self, command: AcceptInvitationCommand) -> MemberResponse:
        invitation = await _get_pending_invitation(self.session, command.token)
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
class RegisterInvitationCommand(BaseCommand):
    token: str
    username: str
    password: str
    password_repeat: str


@dataclass(frozen=True)
class RegisterInvitationHandler(BaseCommandHandler[RegisterInvitationCommand, InvitationRegistrationResponse]):
    session: AsyncSession
    user_repository: UserRepository
    role_repository: RoleRepository
    hash_service: HashService

    async def handle(self, command: RegisterInvitationCommand) -> InvitationRegistrationResponse:
        invitation = await _get_pending_invitation(self.session, command.token)
        existing_email = await self.user_repository.get_by_email(invitation.email)
        if existing_email is not None:
            raise DuplicateUserError(field="email", value=invitation.email)
        normalized_username = command.username.strip()
        existing_username = await self.user_repository.get_by_username(normalized_username)
        if existing_username is not None:
            raise DuplicateUserError(field="username", value=normalized_username)
        if command.password != command.password_repeat:
            raise PasswordMismatchError

        system_role = await self.role_repository.get_with_permission_by_name(RolesEnum.STANDARD_USER.value.name)
        if system_role is None:
            raise NotFoundRoleError(name=RolesEnum.STANDARD_USER.value.name)

        user = User.create(
            email=invitation.email,
            username=normalized_username,
            password_hash=self.hash_service.hash_password(command.password),
            roles={system_role},
            is_verified=True,
        )
        await self.user_repository.create(user)
        await self.session.flush()
        member = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role,
        )
        self.session.add(member)
        invitation.status = InvitationStatus.ACCEPTED
        # Possession of the one-time invitation token is the email verification step.
        user.pull_events()
        await self.session.commit()
        await self.user_repository.invalidate_cache()
        return InvitationRegistrationResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            organization_id=invitation.organization_id,
            role=OrganizationRole(invitation.role),
        )


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
