const integer = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const date = new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", timeZone: "Europe/Moscow" });
const dateTime = new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Moscow" });

export function formatDecimal(value: string, fractionDigits = 0) {
  if (!value.trim()) return "—";
  const normalized = value.trim().replace(",", ".");
  const negative = normalized.startsWith("-");
  const [wholeRaw, fractionRaw = ""] = normalized.replace(/^[+-]/, "").split(".");
  let whole: string;
  try { whole = integer.format(BigInt(wholeRaw || "0")); } catch { return "—"; }
  const fraction = fractionDigits ? fractionRaw.padEnd(fractionDigits, "0").slice(0, fractionDigits) : "";
  return `${negative ? "−" : ""}${whole}${fraction ? `,${fraction}` : ""}`;
}

export const formatMoney = (value: string) => {
  const fraction = value.trim().replace(",", ".").split(".")[1]?.replace(/0+$/, "");
  return `${formatDecimal(value, fraction ? 2 : 0)} ₽`;
};
export const formatCount = (value: string | number) => { try { return integer.format(typeof value === "number" ? value : BigInt(value)); } catch { return "—"; } };
export const formatPercent = (value: string | number) => { const numeric = Number(value); return Number.isFinite(numeric) ? `${percent.format(numeric)}%` : "—"; };
export const formatDate = (value: string | Date) => date.format(new Date(value));
export const formatDateTime = (value: string | Date) => dateTime.format(new Date(value));

export function formatMetric(value: string, unit: "rub" | "percent" | "count") {
  if (unit === "rub") return formatMoney(value);
  if (unit === "percent") return formatPercent(value);
  return formatCount(value);
}
