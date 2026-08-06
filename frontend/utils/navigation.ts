import type { Permission } from "./permissions";

export type ManagementTab = {
  label: string;
  href: "/management/cabinets" | "/management/team" | "/management/sync";
  permission?: Permission;
};

export const managementTabs: ManagementTab[] = [
  { label: "Кабинеты", href: "/management/cabinets", permission: "cabinet:manage" },
  { label: "Команда", href: "/management/team", permission: "team:manage" },
  { label: "Синхронизация", href: "/management/sync" },
];
