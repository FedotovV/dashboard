# Универсальный проектный дашборд

Генератор командного дашборда для PM и PO: одна команда, спринтовая доска, два экрана. Первая поставка считается на моделируемых данных. Живой источник v1 — Jira Cloud или Jira Server.

- [План и вехи](docs/plan.md)
- [Архитектура модулей](docs/architecture.html)
- [План первого шага, M1](docs/m1-plan.md)
- [Пошаговая реализация M1](docs/m1-implementation.md)
- [Релиз-ноутсы M1](docs/m1-release-notes.md)
- [План экрана «Спринт», M2](docs/m2-plan.md)
- [Релиз-ноутсы M2](docs/m2-release-notes.md)
- [Читаемость экрана «Спринт»](docs/m2-ui-polish.md)
- [Каталог метрик](docs/metric-catalog.md)
- [Сопоставление установки](docs/mapping-guide.md)
- [Приёмка](docs/install-acceptance.md)
- Схемы: `schema/`

Проверка контракта: `python3 scripts/check_contracts.py`.

Стенд экрана «Спринт» — редактируемый `fixtures/ui/demo.json`: десять человек, спринт, закрытые задачи, состав, блокеры и burndown. После правки файла:

```bash
python3 -m dashboard.api.preview
```

Команда заново собирает слепок в `var/ui` и открывает `http://127.0.0.1:8765/`. Слушает только localhost. `scripts/generate_ui_demo.py` перезаписывает этот JSON, его запускают только чтобы выбросить правки и сгенерировать стенд заново.
