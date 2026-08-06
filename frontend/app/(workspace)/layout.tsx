import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { serverApiRequest } from "@/utils/api/server";
import type { MemberResponse, OrganizationResponse, PageResult, UserResponse } from "@/utils/api/generated";
import type { SessionViewModel } from "@/utils/api/view-models";

async function getInitialSession(): Promise<SessionViewModel> {
  try {
    const [user, organizations] = await Promise.all([
      serverApiRequest<UserResponse>("/api/v1/users/me"),
      serverApiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
    ]);
    const organization = organizations.items[0];
    if (!organization) return { user };
    const members = await serverApiRequest<PageResult<MemberResponse>>(
      `/api/v1/organizations/${organization.id}/members?page=1&page_size=100`,
    );
    return {
      user,
      organization_name: organization.name,
      role: members.items.find((member) => member.user_id === user.id)?.role
        ?? (organization.owner_user_id === user.id ? "owner" : undefined),
    };
  } catch {
    return {};
  }
}

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const initialSession = await getInitialSession();
  return <Suspense><AppShell initialSession={initialSession}>{children}</AppShell></Suspense>;
}
