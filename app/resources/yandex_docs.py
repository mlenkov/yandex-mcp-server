from mcp.server.fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:

    @mcp.resource("yandex://direct/docs")
    async def direct_docs() -> str:
        """
        Полная документация по Яндекс.Директ API.

        ВКЛЮЧАЕТ: структуру кампаний, статусы, ограничения, best practices.
        """
        return """# Яндекс.Директ API — Полная документация

## Структура данных
- Кампания (Campaign) → Группы (AdGroups) → Объявления (Ads) + Фразы (Keywords)
- Каждая кампания имеет: Id, Name, Status, StartDate, DailyBudget

## Статусы кампаний
- DRAFT — черновик, не запущена
- MODERATION — на проверке
- ACCEPTED — принята, готова к запуску
- RUNNING — активна, показываются объявления
- STOPPED — остановлена вручную
- ENDED — завершена (закончился бюджет или дата)

## Ограничения API
- Максимум 10000 объектов в одном запросе
- Не более 10 запросов в секунду на аккаунт
- Отчёты генерируются асинхронно (требуется polling)

## Типичные сценарии
1. get_direct_campaigns() — список кампаний
2. get_direct_stats(campaign_id, date_from, date_to) — статистика
3. get_direct_keywords(campaign_id) — ключевые слова

## Best practices
- Всегда указывай limit ≤ 500, чтобы не перегружать контекст
- Для больших выборок используй пагинацию через offset
- Проверяй Status перед изменениями (нельзя редактировать MODERATION)
"""

    @mcp.resource("yandex://metrika/docs")
    async def metrika_docs() -> str:
        """Полная документация по Яндекс.Метрика API."""
        return """# Яндекс.Метрика API — Полная документация

## Структура данных
- Счётчик (Counter) → Цели (Goals) → Отчёты (Reports)
- Каждый счётчик имеет: Id, Name, Code (трекинг-код)

## Типы отчётов
- Посещаемость (visits, users, pageviews)
- Источники (traffic sources)
- Конверсии (goals, ecommerce)
- Аудитория (demographics, devices)

## Ограничения API
- Максимум 100000 строк в отчёте
- Не более 5 одновременных запросов на аккаунт
- Отчёты за период > 30 дней генерируются до 5 минут

## Типичные сценарии
1. get_metrika_counters() — список счётчиков
2. get_metrika_stats(counter_id, metrics, date_from, date_to) — статистика
3. get_metrika_goals(counter_id) — цели счётчика
"""

    @mcp.resource("yandex://webmaster/docs")
    async def webmaster_docs() -> str:
        """Полная документация по Яндекс.Вебмастер API."""
        return """# Яндекс.Вебмастер API — Полная документация

## Структура данных
- Хост (Host) → Информация о сайте → Внешние ссылки
- Каждый хост имеет: HostUid, Host, Verified, Indexed

## Статусы верификации
- VERIFIED — сайт подтверждён
- NOT_VERIFIED — сайт не подтверждён

## Типичные сценарии
1. get_webmaster_hosts() — список сайтов
2. get_webmaster_stats(host_uid) — статистика поиска
3. get_webmaster_external_links(host_uid) — внешние ссылки
"""

    @mcp.resource("yandex://audience/docs")
    async def audience_docs() -> str:
        """Полная документация по Яндекс.Аудитории API."""
        return """# Яндекс.Аудитории API — Полная документация

## Структура данных
- Сегмент (Segment) — набор пользователей по заданным условиям
- Каждый сегмент: Id, Name, Type, Size

## Типы сегментов
- RETARGETING — сегменты на основе действий пользователей
- INTERESTS — сегменты на основе интересов
- GEO — географические сегменты
- LOOKALIKE — похожие сегменты

## Типичные сценарии
1. get_audience_segments() — список сегментов
2. get_audience_segment_stats(segment_id) — статистика сегмента
"""

    @mcp.resource("yandex://admetrica/docs")
    async def admetrica_docs() -> str:
        """Полная документация по Яндекс.AdMetrica API."""
        return """# Яндекс.AdMetrica API — Полная документация

## Структура данных
- Кампания (Campaign) — рекламная кампания в системе AdMetrica
- Каждая кампания: Id, Name, Status, Type

## Типичные сценарии
1. get_admetrica_campaigns() — список кампаний
2. get_admetrica_stats(campaign_id) — статистика кампании
"""
