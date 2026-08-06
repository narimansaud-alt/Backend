# Сводка

Закрытый рабочий кабинет аналитики Wildberries, Ozon и Яндекс Маркета на Next.js App Router, React 19, TypeScript и Tailwind CSS 4.

## Быстрый запуск

```bash
pnpm install
pnpm.cmd dev
```

Откройте `http://localhost:3000` — главная перенаправит в `/dashboard`. Для отображения данных нужен `API_URL`; браузерные запросы проходят через same-origin proxy Next.js, поэтому публичный API URL и CORS не ломают интерфейс.

## Настройка backend

Скопируйте `.env.example` в `.env.local` и задайте:

```dotenv
API_URL=https://api.windoweropu.store
NEXT_PUBLIC_API_URL=https://api.windoweropu.store
NEXT_PUBLIC_RELEASE_ID=release-id
```

В PowerShell используйте `pnpm.cmd`, если выполнение `pnpm.ps1` запрещено
политикой ExecutionPolicy. Browser requests идут через same-origin proxy
`/api/backend`; CORS backend нужен только для прямых обращений.

`API_URL` используется Server Components, auth proxy и browser API proxy. `NEXT_PUBLIC_API_URL` оставлен для обратной совместимости сборки. Backend остаётся единственным источником бизнес-метрик и повторно проверяет сессию, роль и cabinet scope.

## Проверка

```bash
pnpm typecheck
pnpm test
pnpm build
```

Подробная архитектура, карта маршрутов и ограничения: [docs/implementation.md](docs/implementation.md).
