import type { Permission } from "./permissions";

export type ManagementTab = {
  label: string;
  href: "/management/organizations" | "/management/cabinets" | "/management/users" | "/management/invitations" | "/management/team" | "/management/sync";
  permission?: Permission;
};

export const managementTabs: ManagementTab[] = [
  { label: "Организации", href: "/management/organizations", permission: "organization:manage" },
  { label: "Кабинеты", href: "/management/cabinets", permission: "cabinet:manage" },
  { label: "Пользователи", href: "/management/users", permission: "user:view" },
  { label: "Инвайты", href: "/management/invitations", permission: "member:invite" },
  { label: "Команда", href: "/management/team", permission: "team:manage" },
  { label: "Синхронизация", href: "/management/sync" },
];
