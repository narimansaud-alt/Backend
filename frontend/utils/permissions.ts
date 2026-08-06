export type Role = "owner" | "admin" | "manager" | "viewer";
export type Permission = "finance:manage" | "plan:manage" | "team:manage" | "cabinet:manage" | "export:read";

const grants: Record<Role, Permission[]> = {
  owner: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read"],
  admin: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read"],
  manager: ["plan:manage", "export:read"],
  viewer: ["export:read"],
};

export function can(role: Role, permission: Permission) { return grants[role].includes(permission); }
