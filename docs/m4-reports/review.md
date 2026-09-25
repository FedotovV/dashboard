# M4. Проверка

Команды: `python3 -m pytest` (124 теста, из них 23 в `tests/test_m4.py`) и `python3 scripts/check_contracts.py` (`contracts ok`). Браузер не поднимался. Ответы читались через `urllib` с `127.0.0.1`.

Сошлось:

- 10 золотых случаев M1 через `run` совпали с записанными числами; `write-once` не сменил байты; `edits.json` не сменился; `rules-changed` не создал слепок;
- байты слепка `run` на `due-midnight` равны прямому `build`;
- `fixtures/m4/file-sprint` совпал с `expected.canonical.json`, слепки побайтно равны;
- `GET /api/sprint` этой выгрузки: `E-1.closedBeforeDue = true`, `N-1 = false`, `D-1.storyPoints = 8`, `R-1.scope = removed`, `burndown.params.storyPointsAtAdd = 8`, подзадачи в составе нет;
- `GET /api/sprint` фикстуры `due-midnight` совпал со строками золотого снимка;
- `live` и адрес кроме `127.0.0.1` не пишут файлы.
