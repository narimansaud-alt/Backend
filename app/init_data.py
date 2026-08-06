import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models.role import Role
from app.auth.models.role_permission import RolesEnum
from app.auth.models.user import User
from app.auth.services.hash import HashService, create_hash_service
from app.core.configs.app import app_config
from app.organizations.models import Organization, OrganizationMember, OrganizationRole


async def create_base_roles(db: AsyncSession) -> None:
    roles = RolesEnum.get_all_roles()
    for base_role in roles:
        role = await db.execute(select(Role).where(Role.name == base_role.name))
        if role.scalar() is None:
            db.add(base_role)

    await db.flush()


def _validate_initial_admin_settings() -> tuple[str, str, str, str] | None:
    values = (
        app_config.INITIAL_ADMIN_EMAIL.strip().casefold(),
        app_config.INITIAL_ADMIN_USERNAME.strip(),
        app_config.INITIAL_ADMIN_PASSWORD,
    )
    if not any(values):
        return None
    if not all(values):
        raise RuntimeError("INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD must be set together")
    email, username, password = values
    if "@" not in email or len(username) < 3:
        raise RuntimeError("Initial administrator email or username is invalid")
    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"[0-9]", password)
        or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    ):
        raise RuntimeError("INITIAL_ADMIN_PASSWORD does not meet the password complexity requirements")
    organization_name = app_config.INITIAL_ORGANIZATION_NAME.strip()
    if len(organization_name) < 2:
        raise RuntimeError("INITIAL_ORGANIZATION_NAME must contain at least 2 characters")
    return email, username, password, organization_name


async def create_initial_admin(db: AsyncSession, hash_service: HashService | None = None) -> None:
    settings = _validate_initial_admin_settings()
    if settings is None:
        return
    email, username, password, organization_name = settings
    role = await db.scalar(select(Role).where(Role.name == RolesEnum.SUPER_ADMIN.value.name))
    if role is None:
        raise RuntimeError("The super_admin role was not initialized")

    users = (
        await db.scalars(
            select(User).options(selectinload(User.roles)).where(or_(User.email == email, User.username == username))
        )
    ).all()
    if len(users) > 1:
        raise RuntimeError("INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_USERNAME belong to different users")
    user = users[0] if users else None
    if user is not None and (user.email != email or user.username != username):
        raise RuntimeError("Initial administrator email or username conflicts with an existing user")
    if user is None:
        hasher = hash_service or create_hash_service()
        user = User.create(
            email=email,
            username=username,
            password_hash=hasher.hash_password(password),
            roles={role},
            is_verified=True,
        )
        user.pull_events()
        db.add(user)
        await db.flush()
    else:
        user.is_active = True
        user.is_verified = True
        user.deleted_at = None
        user.roles.add(role)

    organization = await db.scalar(select(Organization).where(Organization.owner_user_id == user.id))
    if organization is None:
        organization = Organization(name=organization_name, owner_user_id=user.id)
        db.add(organization)
        await db.flush()
    member = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user.id,
        )
    )
    if member is None:
        db.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role=OrganizationRole.OWNER,
            )
        )
    else:
        member.role = OrganizationRole.OWNER
        member.is_active = True


async def init_data(db: AsyncSession, hash_service: HashService | None = None) -> None:
    # Every Gunicorn worker runs the lifespan hook. Serialize bootstrap work so
    # concurrent workers cannot create duplicate roles, users or organizations.
    await db.execute(select(func.pg_advisory_xact_lock(2026080601)))
    try:
        await create_base_roles(db)
        await create_initial_admin(db, hash_service)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
