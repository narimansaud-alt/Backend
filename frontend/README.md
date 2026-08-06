# Сводка

Закрытый рабочий кабинет аналитики Wildberries, Ozon и Яндекс Маркета на Next.js App Router, React 19, TypeScript и Tailwind CSS 4.

## Быстрый запуск

```bash
pnpm install
pnpm dev
```

Откройте `http://localhost:3000` — главная перенаправит в `/dashboard`. Для отображения данных обязательны `API_URL` (server-side запросы) и `NEXT_PUBLIC_API_URL` (browser auth, export и observability). Без backend приложение показывает понятное состояние конфигурационной ошибки и не подставляет локальные данные.

## Настройка backend

Скопируйте `.env.example` в `.env.local` и задайте:

```dotenv
API_URL=https://analytics-api.example.internal
NEXT_PUBLIC_API_URL=https://analytics-api.example.internal
NEXT_PUBLIC_RELEASE_ID=release-id
```

`API_URL` используется Server Components, `NEXT_PUBLIC_API_URL` — для клиентской диагностики. Backend остаётся единственным источником бизнес-метрик и повторно проверяет сессию, роль и cabinet scope.

## Проверка

```bash
pnpm typecheck
pnpm test
pnpm build
```

Подробная архитектура, карта маршрутов и ограничения: [docs/implementation.md](docs/implementation.md).
