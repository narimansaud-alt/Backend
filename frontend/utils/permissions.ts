export type Role = "owner" | "admin" | "manager" | "viewer";
export type Permission = "finance:manage" | "plan:manage" | "team:manage" | "cabinet:manage" | "export:read" | "organization:manage" | "member:invite" | "user:view";

const grants: Record<Role, Permission[]> = {
  owner: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read", "organization:manage", "member:invite", "user:view"],
  admin: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read", "organization:manage", "member:invite", "user:view"],
  manager: ["plan:manage", "export:read"],
  viewer: ["export:read"],
};

export function can(role: Role, permission: Permission) { return grants[role].includes(permission); }
