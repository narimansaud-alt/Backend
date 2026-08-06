import { ExportButton } from "./export-button";

export function PageHeader({ title, description, updated, actions = true }: { title: string; description?: string; updated?: string; actions?: boolean }) {
  return <div className="mb-5 flex flex-wrap items-start justify-between gap-4"><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-[22px] font-semibold leading-8 text-[#20231f]">{title}</h1>{updated && <span className="fresh-badge"><span className="size-1.5 rounded-full bg-[#2e8b69]" />Данные актуальны по {updated}</span>}</div>{description && <p className="mt-1 max-w-3xl text-xs leading-5 text-[#747a73]">{description}</p>}</div>{actions && <ExportButton filename={`${title.toLowerCase().replaceAll(" ", "-")}.csv`} />}</div>;
}
