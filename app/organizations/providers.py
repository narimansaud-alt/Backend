from dishka import Provider, Scope, decorate, provide

from app.core.mediators.base import CommandRegistry, QueryRegistry
from app.organizations.commands import (
    AcceptInvitationCommand,
    AcceptInvitationHandler,
    CreateOrganizationCommand,
    CreateOrganizationHandler,
    InviteMemberCommand,
    InviteMemberHandler,
    RemoveMemberCommand,
    RemoveMemberHandler,
    UpdateMemberCommand,
    UpdateMemberHandler,
)
from app.organizations.queries import (
    ListMembersHandler,
    ListMembersQuery,
    ListOrganizationsHandler,
    ListOrganizationsQuery,
)
from app.organizations.repositories import MemberRepository, OrganizationRepository
from app.organizations.services import OrganizationScopeService


class OrganizationsProvider(Provider):
    scope = Scope.REQUEST

    organization_repository = provide(OrganizationRepository)
    member_repository = provide(MemberRepository)
    scope_service = provide(OrganizationScopeService)
    create_organization = provide(CreateOrganizationHandler)
    invite_member = provide(InviteMemberHandler)
    accept_invitation = provide(AcceptInvitationHandler)
    update_member = provide(UpdateMemberHandler)
    remove_member = provide(RemoveMemberHandler)
    list_organizations = provide(ListOrganizationsHandler)
    list_members = provide(ListMembersHandler)

    @decorate
    def commands(self, registry: CommandRegistry) -> CommandRegistry:
        registry.register_command(CreateOrganizationCommand, CreateOrganizationHandler)
        registry.register_command(InviteMemberCommand, InviteMemberHandler)
        registry.register_command(AcceptInvitationCommand, AcceptInvitationHandler)
        registry.register_command(UpdateMemberCommand, UpdateMemberHandler)
        registry.register_command(RemoveMemberCommand, RemoveMemberHandler)
        return registry

    @decorate
    def queries(self, registry: QueryRegistry) -> QueryRegistry:
        registry.register_query(ListOrganizationsQuery, ListOrganizationsHandler)
        registry.register_query(ListMembersQuery, ListMembersHandler)
        return registry
