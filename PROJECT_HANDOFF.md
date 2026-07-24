# YC Startup Radar — выжимка проекта для переноса в новый чат

> Скопируй этот файл целиком в новый чат как контекст. Он описывает цель,
> архитектуру, текущее состояние, стиль работы и следующие шаги.

## 1. Что это за проект и зачем

**YC Startup Radar** — личный инструмент для поиска и оценки интересных стартапов
Y Combinator из батчей **2024–2026** для самостоятельного инвестанализа.

Владелец (я): русскоязычный, программирую в **Google Colab**. Цель — собрать
максимум открытой информации по каждому стартапу в **красивый Excel** + удобный
**интерактивный дашборд**, чтобы фильтровать, помечать и вести свой шорт-лист.

Что важно в данных: индустрия/подиндустрия, краткое описание идеи и уникальности,
статус/investability, состав/размер команды, батч, открытые ссылки для дип-дайва,
AI-описание идеи и рисков.

## 2. Текущее состояние (готово и работает)

- Пайплайн (fetch → normalize → enrich → score → AI → export) — **готов**, 53 теста
  зелёные, ruff/black чисто.
- **Excel + Parquet + CSV** экспорт — готов. Реальный датасет собран: **1736 компаний**
  (батчи 2024/2025/2026), у всех есть AI-описания. Лежит в репо:
  `data/processed/yc_radar.parquet` (~1.6 МБ, публичные данные YC).
- **Streamlit-дашборд** — готов и **задеплоен на Streamlit Community Cloud**, работает
  по постоянной ссылке (деплой с ветки `main`).
- AI-описания — через **Claude Haiku 4.5** (платно, ~3–4 USD за полный набор),
  синхронно, с возобновляемым кэшем. Бесплатная альтернатива — Groq (в коде есть).
- Персистентность заметок на хостинге — через **Google Sheets** (бэкенд написан).

### Что сейчас в процессе (последний шаг)
Подключение **Google Sheets** как хранилища заметок на Streamlit Cloud. Я прошёл:
создал GCP-проект, включил Sheets API + Drive API, создал **service account**,
скачал **JSON-ключ**. Осталось: (5a) создать Google-таблицу и расшарить её на email
сервис-аккаунта как Editor; (5b) вставить секреты в Streamlit (Settings → Secrets)
по шаблону — секция `[gcp_service_account]` из JSON, `[gsheets]` со ссылкой на
таблицу, `[app] owner_key`. Ключевая засада — поле `private_key`: копировать как есть
со всеми `\n`, не переносить строки.

> Важно: Google Sheets API **бесплатен и без карты** — нужен именно service account
> (не API key/OAuth), биллинг-баннер пропускается.

## 3. Технологический стек

- **Python 3.11**, pandas 2.2, httpx, pyarrow (Parquet), openpyxl (Excel).
- **Streamlit** (дашборд) + **Plotly** (интерактивные графики).
- **Anthropic Claude** (Haiku 4.5) для AI-описаний; опционально **Groq** (бесплатно).
- **Google Sheets** (gspread + google-auth) — хранилище заметок на хостинге.
- Тесты: **pytest** (сеть и AI полностью замоканы). Линт: **ruff**, формат: **black**
  (line-length 100).
- Данные YC: публичный `yc-oss/api` → `https://yc-oss.github.io/api/companies/all.json`.
- Запуск: **Google Colab** (основной), **Streamlit Cloud** (хостинг дашборда),
  **GitHub Actions** (сборка данных «fire-and-forget»).

## 4. Архитектура и файлы

Репозиторий: **`Nerbi357/VC-Tracking`** (приватный).

```
src/yc_radar/            переиспользуемая протестированная логика
  fetch.py       fetch_companies(*, force_refresh, cache_path, max_age_hours, url)
  normalize.py   normalize(records, *, years=(2024,2025,2026)); parse_batch_year()
  enrich.py      add_investability(df) [INVESTABILITY dict], add_links(df) [только открытые ссылки]
  score.py       score(df, *, weights=DEFAULT_WEIGHTS) -> 0..100
  ai.py          make_claude_summarizer(...), make_groq_summarizer(...), add_ai_summaries(...)
  export.py      export(df, *, out_dir) -> parquet/xlsx/csv (чистит control-символы)
  filters.py     apply_filters(...) + split_tags()/all_tags()
  user_data.py   аннотации: USER_COLUMNS, STAGES, merge_annotations/merge_user_data/coerce_types
  gsheets.py     Google Sheets бэкенд: is_configured/load/save
app.py                   Streamlit-дашборд (4 вкладки), читает Parquet, не рефетчит
notebooks/
  yc_radar_colab.ipynb   ГЛАВНАЯ тетрадь: self-contained для Colab (пишет свой модуль+app, Google Drive)
  yc_radar.ipynb         локальная версия
scripts/run_pipeline.py  headless-раннер для GitHub Actions
.github/workflows/build-radar.yml  workflow_dispatch, артефакт yc-radar
data/processed/yc_radar.parquet    реальный датасет (закоммичен для хостинга)
requirements.txt  pyproject.toml   зависимости и конфиг ruff/black/pytest
SPEC.md  tasks/plan.md  tasks/todo.md   спека и план (13 задач, все done)
HOSTING.md               пошаговый гайд по Streamlit Cloud + Google Sheets + шеринг
.streamlit/secrets.toml.example   шаблон секретов (gsheets + owner_key)
README.md                обзор
tests/                   pytest (network+AI замоканы), 53 теста
```

### Дашборд `app.py` — 4 вкладки
- **📊 Обзор** — KPI-карточки + Plotly-графики (индустрии/подиндустрии, годы батча,
  распределение score, статусы, воронка) + топ-N лидерборд.
- **🔎 Компании** — таблица + карточки, кнопки «скачать отфильтрованное» CSV/Excel.
- **⚖️ Сравнение** — до 5 компаний бок о бок.
- **📝 Заметки** — rating, ⭐ избранное, стадия воронки, теги, заметки.

Фильтры (сайдбар): индустрия, подиндустрия, статус, investability, стадия воронки,
теги, «только избранные», год батча, диапазоны score и размера команды, поиск.

### Режим владелец/гость (для шеринга ссылки)
- `[app] owner_key` в секретах. Владелец вводит ключ в сайдбаре → появляется 💾 Save
  (пишет в Google Sheets). Гости без ключа — **режим просмотра**: могут крутить и даже
  править таблицу заметок, но правки временные (в сессии), не влияют на заметки
  владельца, исчезают при обновлении; могут скачать свои правки в CSV.
- Если `owner_key` не задан (локально/Colab) — одиночный режим, полный доступ на запись.

## 5. Модель данных (аннотации)

`user_data.USER_COLUMNS = ("slug", "my_rating", "watchlist", "my_tags", "my_stage", "my_notes")`
- `slug` — ключ джойна; `watchlist` — ⭐ избранное (bool);
- `my_stage` — стадия воронки из `STAGES = ("New","To review","Contacted","Passed","Invested")`, дефолт `"New"`;
- `my_tags` — свободные теги через запятую; `my_rating` — Int64 (0–5); `my_notes` — текст.

`merge_annotations(df, user)` идемпотентен: если колонки аннотаций уже есть в `df`,
он их сбрасывает перед джойном (иначе pandas делал бы `_x/_y` → был баг KeyError
'watchlist', уже пофикшено).

Хранилище выбирается автоматически: **Google Sheets**, если настроены секреты, иначе
локальный **CSV** (`data/user_data.csv`).

## 6. Как запускается

- **Colab (основной путь):** открыть `notebooks/yc_radar_colab.ipynb` → Run all.
  Тетрадь self-contained: ставит зависимости (вкл. plotly), монтирует Google Drive
  (`/content/drive/MyDrive/VC PROJECT FINAL`), пишет `%%writefile yc_radar_pipeline.py`
  и `%%writefile app.py`, берёт `ANTHROPIC_API_KEY` из Colab Secrets, собирает Excel,
  запускает Streamlit через cloudflared-туннель. Данные и кэш — на Google Drive
  (переживают перезапуск).
- **Streamlit Cloud (хостинг дашборда):** деплой с ветки `main`, main file `app.py`,
  читает `data/processed/yc_radar.parquet`.
- **GitHub Actions:** `build-radar.yml`, workflow_dispatch, вход `use_ai`, секреты
  `ANTHROPIC_API_KEY`/`GROQ_API_KEY`, артефакт `yc-radar`, timeout 90 мин.

## 7. Git: ветки и конвенции

- Рабочая ветка: **`claude/ycombinator-startups-agent-skills-eyv4ar`**.
- Ветка `main` = деплой Streamlit Cloud. Изменения сначала в рабочую ветку, потом
  вливаются в `main` (с моего явного разрешения).
- Последние коммиты: `3beee3d` (owner/viewer), `603344e` (upload датасета),
  `f79e7c1` (апгрейд дашборда). `main` на `1977ca6`.
- Коммиты заканчиваются:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` и строкой `Claude-Session:`.
- Push: `git push -u origin <branch>`, ретраи с backoff при сетевых ошибках.
- PR **не** создавать без явной просьбы.

## 8. Принципы и ограничения (соблюдать всегда)

- **Только открытые/бесплатные ресурсы.** Никаких платных/закрытых ссылок
  (Crunchbase, LinkedIn и т.п.).
- **Не выдумывать цифры.** Cap table и точные суммы раундов для приватных стартапов
  публично не существуют — их НЕ фабрикуем. `investability` — честная эвристика от
  статуса, не «настоящие» деньги.
- **Секреты не коммитить** (`.env`, ключи, service-account JSON) — только через Colab
  Secrets / GitHub Secrets / Streamlit Secrets. `.streamlit/secrets.toml` в .gitignore.
- **AI списывает деньги только при наличии ключа** и только на машине, где запущен
  пайплайн (у меня в Colab/Actions), не на стороне ассистента. Нет ключа → плейсхолдер,
  ноль трат.
- Технический идентификатор модели ассистента не должен попадать в коммиты и
  артефакты (в сообщениях коммитов — только имя вида «Claude Opus 4.8»).

## 9. Стиль и алгоритм работы (как мы работаем)

- **Язык общения — русский.** Отвечать по-русски, код/комментарии — по-английски.
- **Сначала предлагаю варианты — потом пишу код.** На вопросах «как лучше» — даю
  рекомендацию и жду решения, не пишу код вслепую.
- Объясняю **пошагово и явно**, с учётом того, что я работаю в **Colab** (часто прошу
  «скажи, что делать по шагам» и «какие ячейки переписать»).
- Держу **честность про данные** (см. п.8) и **бюджет** (для AI — важнее качество
  вывода, чем экономия, но в пределах ~3–4 USD).
- После изменений — прогоняю **тесты + ruff + black**, потом коммит с внятным
  сообщением, потом пуш.
- Когда что-то падает — сначала диагностирую причину (напр., по traceback), потом
  чиню; не гадаю.
- **Fire-and-forget** и защита от потери данных важны (Google Drive, кэш, Actions).

## 10. Что дальше / открытые задачи

1. **Дозавершить Google Sheets** (шаг 5a+5b выше) и проверить сохранение заметок на
   хостинге (появится вкладка `annotations` в таблице).
2. Опционально — **прятать заметки владельца от гостей** (флаг `hide_owner_notes`).
3. Опционально — **персональные заметки у каждого гостя** (настоящий логин
   `st.login`/Google OIDC + вкладка на пользователя) — полноценный многопользовательский
   режим.
4. Возможные улучшения дашборда: подсветка новых компаний с прошлого обновления,
   переключение видимости колонок, ещё графики.

## 11. Что приложить в новом чате

- Этот файл (`PROJECT_HANDOFF.md`).
- Доступ к репозиторию `Nerbi357/VC-Tracking` (ветка
  `claude/ycombinator-startups-agent-skills-eyv4ar`).
- Файлы для быстрого старта, если репо недоступен: `app.py`, `src/yc_radar/*.py`,
  `notebooks/yc_radar_colab.ipynb`, `HOSTING.md`, `.streamlit/secrets.toml.example`.
