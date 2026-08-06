"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronsUpDown, Columns3, Search } from "lucide-react";
import type { CellFormat } from "@/utils/operational-pages";
import { formatCount, formatMoney, formatPercent } from "@/utils/formatters";

type Column = { key: string; label: string; format: CellFormat };
type Cell = string | number | null;

function renderCell(value: Cell, format: CellFormat) {
  if (value === null || value === undefined || value === "") return "—";
  if (format === "money") return formatMoney(String(value));
  if (format === "percent") return formatPercent(value);
  if (format === "number") return formatCount(value);
  if (format === "status") return <span className={`status-badge status-${String(value).toLowerCase().replaceAll(" ", "-")}`}>{value}</span>;
  return value;
}

export function DataTable({ columns, rows, searchLabel = "Найти в отчёте", emptyMessage = "Backend не вернул строк за выбранный период." }: { columns: Column[]; rows: Array<Record<string, Cell>>; searchLabel?: string; emptyMessage?: string }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: string; asc: boolean }>();
  const [visible, setVisible] = useState(() => columns.map((column) => column.key));
  const [chooser, setChooser] = useState(false);
  const [page, setPage] = useState(1);
  const data = useMemo(() => {
    const filtered = rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLocaleLowerCase("ru").includes(query.toLocaleLowerCase("ru"))));
    if (!sort) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sort.key] ?? ""; const bv = b[sort.key] ?? "";
      const result = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv), "ru", { numeric: true });
      return sort.asc ? result : -result;
    });
  }, [rows, query, sort]);
  const shown = columns.filter((column) => visible.includes(column.key));
  const pageSize = 8;
  const pages = Math.max(1, Math.ceil(data.length / pageSize));
  const safePage = Math.min(page, pages);
  const pageRows = data.slice((safePage - 1) * pageSize, safePage * pageSize);
  const toggleSort = (key: string) => setSort((current) => current?.key === key ? { key, asc: !current.asc } : { key, asc: true });

  return <>
    <div className="flex flex-wrap items-center gap-2 border-b border-[#e5e7e2] p-3"><div className="relative min-w-[220px] flex-1 sm:max-w-xs"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#929790]" size={14} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} className="h-8 w-full rounded-md border border-[#dfe2dc] bg-white pl-8 pr-3 text-xs outline-none focus:border-[#34745f]" placeholder={searchLabel} aria-label={searchLabel} /></div><div className="relative"><button className="secondary-button h-8" onClick={() => setChooser((value) => !value)} aria-expanded={chooser}><Columns3 size={14} />Колонки<ChevronDown size={13} /></button>{chooser && <div className="absolute right-0 top-10 z-20 w-52 rounded-md border border-[#dfe2dc] bg-white p-2 shadow-lg">{columns.map((column) => <label key={column.key} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-[#f4f5f3]"><input type="checkbox" checked={visible.includes(column.key)} disabled={visible.length === 1 && visible.includes(column.key)} onChange={() => setVisible((value) => value.includes(column.key) ? value.filter((key) => key !== column.key) : [...value, column.key])} />{column.label}</label>)}</div>}</div></div>
    <div className="table-scroll"><table className="data-table"><thead><tr>{shown.map((column) => <th key={column.key} className={column.format === "money" || column.format === "number" || column.format === "percent" ? "numeric" : ""}><button onClick={() => toggleSort(column.key)} className="inline-flex items-center gap-1 whitespace-nowrap font-semibold">{column.label}<ChevronsUpDown size={12} className="text-[#adb1ac]" /></button></th>)}</tr></thead><tbody>{pageRows.length ? pageRows.map((row, index) => <tr key={index}>{shown.map((column) => <td key={column.key} className={`${column.format === "money" || column.format === "number" || column.format === "percent" ? "numeric" : ""} ${column === shown[0] ? "sticky-cell" : ""}`}>{renderCell(row[column.key], column.format)}</td>)}</tr>) : <tr><td colSpan={shown.length} className="py-12 text-center text-[#858b84]">{emptyMessage}</td></tr>}</tbody></table></div>
    <div className="flex items-center justify-between border-t border-[#e5e7e2] px-3 py-2.5 text-[11px] text-[#858b84]"><span>Показано {pageRows.length} из {data.length}</span><div className="flex items-center gap-2"><button className="icon-button" disabled={safePage <= 1} onClick={() => setPage((value) => value - 1)} aria-label="Предыдущая страница"><ChevronLeft size={15} /></button><span className="tabular-nums">{safePage} / {pages}</span><button className="icon-button" disabled={safePage >= pages} onClick={() => setPage((value) => value + 1)} aria-label="Следующая страница"><ChevronRight size={15} /></button></div></div>
  </>;
}
