import { afterEach, describe, expect, it, vi } from "vitest";
import { formatMoney, formatPercent } from "../utils/formatters";
import { activeFilterCount, parseFilters, serializeFilters } from "../utils/filters";
import type { FilterState } from "../utils/filters";
import { can } from "../utils/permissions";
import { sanitizeText } from "../utils/error-sanitizer";
import { apiRequest, ApiError } from "../utils/api/client";
import { managementTabs } from "../utils/navigation";

describe("formatters", () => {
  it("форматирует денежную строку без преобразования в Number", () => expect(formatMoney("9874200.00")).toBe("9 874 200 ₽"));
  it("форматирует проценты по ru-RU", () => expect(formatPercent("18.7")).toBe("18,7%"));
});

describe("URL filters", () => {
  it("сохраняет массивы в ссылке и восстанавливает их", () => {
    const source: FilterState = { date_from: "2026-07-05", date_to: "2026-08-03", marketplaces: ["wildberries", "ozon"], cabinet_ids: ["one"] };
    const result = parseFilters(serializeFilters(source));
    expect(result.marketplaces).toEqual(["wildberries", "ozon"]);
    expect(result.cabinet_ids).toEqual(["one"]);
    expect(activeFilterCount(result)).toBe(2);
  });
});

describe("permissions", () => {
  it("не даёт viewer изменять финансы", () => expect(can("viewer", "finance:manage")).toBe(false));
  it("даёт owner управлять командой", () => expect(can("owner", "team:manage")).toBe(true));
  it("показывает владельцу вкладки команды и кабинетов", () => {
    const ownerTabs = managementTabs
      .filter((item) => !item.permission || can("owner", item.permission))
      .map((item) => item.href);
    expect(ownerTabs).toContain("/management/team");
    expect(ownerTabs).toContain("/management/cabinets");
    expect(ownerTabs).toContain("/management/organizations");
    expect(ownerTabs).toContain("/management/invitations");
  });
});

describe("error sanitization", () => {
  it("удаляет токены, email и секреты query", () => {
    const result = sanitizeText("Bearer abc123 email=user@example.com&token=secret");
    expect(result).not.toContain("abc123"); expect(result).not.toContain("user@example.com"); expect(result).not.toContain("secret");
  });
});

describe("API error mapping", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("превращает 403 в состояние доступа и сохраняет request id", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "forbidden" }), { status: 403, headers: { "x-request-id": "req-42", "content-type": "application/json" } })));
    await expect(apiRequest("/private", { baseUrl: "https://api.example" })).rejects.toMatchObject({ status: 403, requestId: "req-42" } satisfies Partial<ApiError>);
  });

  it("обновляет токен при backend-ответе 403 INVALID_TOKEN", async () => {
    vi.stubGlobal("window", { location: { pathname: "/private", search: "", assign: vi.fn() } });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "INVALID_TOKEN", message: "Invalid token" } }), { status: 403 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "fresh-access-token" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ ok: boolean }>("/private", { baseUrl: "https://api.example" })).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({ headers: expect.objectContaining({ authorization: "Bearer fresh-access-token" }) });
  });
});
