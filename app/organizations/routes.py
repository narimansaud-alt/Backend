from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, Response, status

from app.auth.deps import AuthCurrentUserJWTData
from app.core.db.repository import PageResult
from app.core.mediators.base import BaseMediator
from app.organizations.commands import (
    AcceptInvitationCommand,
    CreateOrganizationCommand,
    InviteMemberCommand,
    RemoveMemberCommand,
    UpdateMemberCommand,
)
from app.organizations.queries import ListMembersQuery, ListOrganizationsQuery
from app.organizations.schemas import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationResponse,
    MemberResponse,
    MemberUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
)

router = APIRouter(prefix="/organizations", tags=["organizations"], route_class=DishkaRoute)


@router.get("")
async def list_organizations(
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[OrganizationResponse]:
    return await mediator.handle_query(ListOrganizationsQuery(user=user, page=page, page_size=page_size))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreateRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> OrganizationResponse:
    return await mediator.handle_command(CreateOrganizationCommand(user=user, name=request.name))


@router.get("/{organization_id}/members")
async def list_members(
    organization_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[MemberResponse]:
    return await mediator.handle_query(
        ListMembersQuery(user=user, organization_id=organization_id, page=page, page_size=page_size)
    )


@router.post("/{organization_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_member(
    organization_id: UUID,
    request: InvitationCreateRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> InvitationResponse:
    return await mediator.handle_command(
        InviteMemberCommand(
            user=user,
            organization_id=organization_id,
            email=str(request.email),
            role=request.role,
            expires_in_hours=request.expires_in_hours,
        )
    )


@router.post("/invitations/accept")
async def accept_invitation(
    request: InvitationAcceptRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> MemberResponse:
    return await mediator.handle_command(AcceptInvitationCommand(user=user, token=request.token))


@router.patch("/{organization_id}/members/{member_id}")
async def update_member(
    organization_id: UUID,
    member_id: UUID,
    request: MemberUpdateRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> MemberResponse:
    return await mediator.handle_command(
        UpdateMemberCommand(
            user=user,
            organization_id=organization_id,
            member_id=member_id,
            role=request.role,
            cabinet_ids=frozenset(request.cabinet_ids),
        )
    )


@router.delete("/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    organization_id: UUID,
    member_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> Response:
    await mediator.handle_command(RemoveMemberCommand(user=user, organization_id=organization_id, member_id=member_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
