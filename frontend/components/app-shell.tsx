"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Activity, BarChart3, BadgeRussianRuble, Boxes, ChevronDown, ChevronRight, CircleDollarSign, Gauge, LayoutDashboard, Menu, PackageSearch, PanelLeftClose, PanelLeftOpen, PieChart, Search, Settings2, ShoppingBag, Target, Users, Warehouse, X, Zap } from "lucide-react";
import { apiRequest } from "@/utils/api/client";
import { can, type Permission } from "@/utils/permissions";
import { managementTabs } from "@/utils/navigation";
import type { CabinetResponse, MemberResponse, OrganizationResponse, PageResult, UserResponse } from "@/utils/api/generated";
import type { SessionViewModel } from "@/utils/api/view-models";
import type { LucideIcon } from "lucide-react";

type NavItem = { label: string; href: string; icon: LucideIcon; permission?: Permission };
type NavSection = { label?: string; items: NavItem[] };
const managementIcons: Record<(typeof managementTabs)[number]["href"], LucideIcon> = {
  "/management/cabinets": PackageSearch,
  "/management/team": Users,
  "/management/sync": Settings2,
};

const navigationSections: NavSection[] = [
  { items: [{ label: "Оцифровка", href: "/dashboard", icon: LayoutDashboard }, { label: "Рука на пульсе", href: "/pulse", icon: Activity }, { label: "Сводный отчёт", href: "/reports/summary", icon: BarChart3 }] },
  { label: "Товары", items: [{ label: "Все товары", href: "/products", icon: ShoppingBag }, { label: "Юнит-экономика", href: "/products/unit-economics", icon: PieChart }, { label: "Остатки", href: "/products/stocks", icon: Warehouse }] },
  { label: "Финансы", items: [{ label: "Прибыли и убытки", href: "/finance/profit-loss", icon: BadgeRussianRuble }, { label: "Движение денег", href: "/finance/cash-flow", icon: CircleDollarSign }, { label: "Операции", href: "/finance/transactions", icon: Zap }, { label: "Расходы", href: "/finance/expenses", icon: Gauge }] },
  { label: "Планирование", items: [{ label: "Реклама", href: "/advertising", icon: Target }, { label: "План-факт", href: "/plan-fact", icon: Boxes }] },
  { label: "Управление", items: managementTabs.map((item) => ({ ...item, icon: managementIcons[item.href] })) },
];

export function AppShell({ children, initialSession = {} }: { children: React.ReactNode; initialSession?: SessionViewModel }) {
  const pathname = usePathname(); const searchParams = useSearchParams();
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false); const [session, setSession] = useState<SessionViewModel>(initialSession);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [cabinets, setCabinets] = useState<CabinetResponse[]>([]);
  const [organizationMenuOpen, setOrganizationMenuOpen] = useState(false);
  const [cabinetMenuOpen, setCabinetMenuOpen] = useState(false);
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  useEffect(() => {
    let active = true;
    Promise.all([
      apiRequest<UserResponse>("/api/v1/users/me"),
      apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
      apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100").catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0, has_next: false, has_previous: false, next_page: null, previous_page: null })),
    ]).then(async ([user, organizationPage, cabinetPage]) => {
      const organization = organizationPage.items[0];
      const members = organization ? await apiRequest<PageResult<MemberResponse>>(`/api/v1/organizations/${organization.id}/members?page=1&page_size=100`).catch(() => null) : null;
      if (!active) return;
      setOrganizations(organizationPage.items);
      setCabinets(cabinetPage.items);
      setSession({ user, organization_name: organization?.name, role: members?.items.find((member) => member.user_id === user.id)?.role });
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  const role = session.role ?? "viewer";
  const visibleSections = useMemo(() => navigationSections.map((section) => ({ ...section, items: section.items.filter((item) => !item.permission || can(role, item.permission)) })).filter((section) => section.items.length), [role]);
  const filterHref = (key: "organization_ids" | "cabinet_ids", value?: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value); else params.delete(key);
    if (key === "organization_ids") params.delete("cabinet_ids");
    const query = params.toString();
    return `${pathname}${query ? `?${query}` : ""}`;
  };
  const selectedCabinet = cabinets.find((cabinet) => cabinet.id === searchParams.get("cabinet_ids"));
  const sidebar = <><div className="flex h-16 items-center justify-between border-b border-white/10 px-4"><Link href={`/dashboard${suffix}`} className="flex min-w-0 items-center gap-3 text-white" aria-label="Оцифровка"><span className="grid size-8 shrink-0 place-items-center rounded-md bg-[#c7f36b] text-[#18362c]"><BarChart3 size={18} /></span>{!collapsed && <span className="font-nacelle text-base font-semibold">Оцифровка</span>}</Link><button className="icon-button hidden text-white/65 hover:bg-white/10 hover:text-white lg:grid" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}>{collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}</button><button className="icon-button text-white/65 lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Закрыть меню"><X size={20} /></button></div><nav className="scrollbar-thin flex-1 overflow-y-auto px-2 py-3" aria-label="Основная навигация">{visibleSections.map((section, index) => <div key={section.label ?? index} className={index ? "mt-4" : ""}>{section.label && !collapsed && <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[.12em] text-white/35">{section.label}</div>}<div className="space-y-0.5">{section.items.map((item) => { const active = pathname === item.href || (item.href === "/products" && pathname.startsWith("/products/")); const Icon = item.icon; return <Link key={item.href} href={`${item.href}${suffix}`} title={collapsed ? item.label : undefined} onClick={() => setMobileOpen(false)} className={`nav-item ${active ? "nav-item-active" : ""} ${collapsed ? "justify-center px-2" : ""}`} aria-current={active ? "page" : undefined}><Icon size={17} className="shrink-0" />{!collapsed && <span className="truncate">{item.label}</span>}</Link>; })}</div></div>)}</nav><div className="border-t border-white/10 p-3"><div className={`flex items-center gap-3 rounded-md p-2 text-white/75 ${collapsed ? "justify-center" : ""}`}><span className="grid size-8 shrink-0 place-items-center rounded-full bg-white/10 text-xs font-semibold text-white">{session.organization_name?.slice(0, 2).toUpperCase() ?? "—"}</span>{!collapsed && <span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-white">{session.organization_name ?? "Организация"}</span><span className="block truncate text-[10px] text-white/45">{session.role ?? "роль не определена"}</span></span>}<ChevronRight size={15} /></div></div></>;
  return <div className="min-h-screen bg-[#f4f5f3]"><aside className={`fixed inset-y-0 left-0 z-40 hidden bg-[#18362c] transition-[width] duration-200 lg:flex lg:flex-col ${collapsed ? "w-[68px]" : "w-[232px]"}`}>{sidebar}</aside>{mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button className="absolute inset-0 bg-black/35" onClick={() => setMobileOpen(false)} aria-label="Закрыть меню" /><aside className="relative flex h-full w-[280px] flex-col bg-[#18362c] shadow-xl">{sidebar}</aside></div>}<div className={`transition-[padding] duration-200 ${collapsed ? "lg:pl-[68px]" : "lg:pl-[232px]"}`}><header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-[#dfe2dc] bg-white/95 px-4 backdrop-blur md:px-6"><button className="icon-button lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Открыть меню"><Menu size={20} /></button><div className="relative hidden max-w-sm flex-1 md:block"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#858b84]" size={16} /><input className="h-9 w-full rounded-md border border-[#dfe2dc] bg-[#f7f8f6] pl-9 pr-3 text-xs outline-none focus:border-[#34745f]" placeholder="Найти товар, отчёт или кабинет" aria-label="Поиск" /></div><div className="ml-auto flex items-center gap-2"><div className="relative hidden sm:block"><button type="button" className="top-control" onClick={() => { setOrganizationMenuOpen((value) => !value); setCabinetMenuOpen(false); }} aria-expanded={organizationMenuOpen} aria-haspopup="menu">{session.organization_name ?? organizations[0]?.name ?? "Организация"}<ChevronDown size={14} /></button>{organizationMenuOpen && <div className="absolute right-0 top-11 z-50 w-64 rounded-md border border-[#dfe2dc] bg-white p-1.5 shadow-lg" role="menu"><p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[#929790]">Организация</p>{organizations.length ? organizations.map((organization) => <Link key={organization.id} href={filterHref("organization_ids", organization.id)} onClick={() => setOrganizationMenuOpen(false)} className="block rounded px-2.5 py-2 text-xs text-[#555b54] hover:bg-[#f4f5f3]" role="menuitem">{organization.name}</Link>) : <p className="px-2.5 py-2 text-xs text-[#929790]">Нет доступных организаций</p>}</div>}</div><div className="relative"><button type="button" className="top-control" onClick={() => { setCabinetMenuOpen((value) => !value); setOrganizationMenuOpen(false); }} aria-expanded={cabinetMenuOpen} aria-haspopup="menu"><span className="size-2 rounded-full bg-[#34745f]" />{selectedCabinet?.name ?? "Все кабинеты"}<ChevronDown size={14} /></button>{cabinetMenuOpen && <div className="absolute right-0 top-11 z-50 w-64 rounded-md border border-[#dfe2dc] bg-white p-1.5 shadow-lg" role="menu"><p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[#929790]">Кабинет</p><Link href={filterHref("cabinet_ids")} onClick={() => setCabinetMenuOpen(false)} className="block rounded px-2.5 py-2 text-xs text-[#555b54] hover:bg-[#f4f5f3]" role="menuitem">Все кабинеты</Link>{cabinets.length ? cabinets.map((cabinet) => <Link key={cabinet.id} href={filterHref("cabinet_ids", cabinet.id)} onClick={() => setCabinetMenuOpen(false)} className="block rounded px-2.5 py-2 text-xs text-[#555b54] hover:bg-[#f4f5f3]" role="menuitem">{cabinet.name}<span className="ml-1 text-[10px] text-[#929790]">· {cabinet.marketplace}</span></Link>) : <p className="px-2.5 py-2 text-xs text-[#929790]">Нет подключённых кабинетов</p>}</div>}</div></div></header><main className="min-h-[calc(100vh-64px)] p-4 md:p-6 xl:p-7">{children}</main></div></div>;
}
