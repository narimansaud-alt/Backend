from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.organizations.models import OrganizationRole


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    owner_user_id: int
    is_active: bool


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    user_id: int
    role: OrganizationRole
    is_active: bool


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: OrganizationRole
    expires_in_hours: int = Field(default=72, ge=1, le=168)


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: OrganizationRole
    status: str
    expires_at: datetime
    invite_token: str | None = None


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class MemberUpdateRequest(BaseModel):
    role: OrganizationRole
    cabinet_ids: set[UUID] = Field(default_factory=set)
