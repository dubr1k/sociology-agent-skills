# Skills в шести агентных оболочках

Справка для разработчика установщика и пользователей набора социологических навыков. Пути и способы вызова сверены с официальной документацией и, где указано, исходным кодом **9 ноября 2026 года**. Это проверка документированной поддержки, а не отчёт о запуске адаптаций: ни одна из шести публичных адаптаций при этой проверке не устанавливалась и не выполнялась.

Машиночитаемая версия — [harnesses.json](harnesses.json): массив из шести записей. `project_skills_dir` — относительный путь внутри проекта, а для OpenClaw — внутри выбранного workspace. `user_skills_dir` содержит значение по умолчанию; переопределения и профильные пути описаны в `notes`. `tool_names` — подтверждённые имена, не обещание доступности всех инструментов в каждой сессии. `verified_basis.runtime_execution: false` прямо отмечает отсутствие исполняемой проверки.

## Целевые каталоги установщика

| Оболочка | Проект / workspace | Пользователь, по умолчанию | Явный вызов |
| --- | --- | --- | --- |
| Hermes | `.hermes/skills` | `~/.hermes/skills` | `/<skill-name>` |
| OpenClaw | `skills` относительно workspace | `~/.openclaw/skills` | `$<skill-command-name>`; ведущая `/<skill-command-name>` |
| Claude Code | `.claude/skills` | `~/.claude/skills` | `/<skill-name>` |
| Codex | `.agents/skills` | `~/.agents/skills` | `$<skill-name>`; выбор через `/skills` |
| Pi | `.pi/skills` | `~/.pi/agent/skills` | `/skill:<skill-name>` |
| Oh My Pi | `.omp/skills` | `~/.omp/agent/skills` | `/skill:<skill-name>` при включённых командах |

Во всех строках устанавливается каталог навыка с файлом `SKILL.md`, например `.omp/skills/thematic-analysis/SKILL.md`. Имена в угловых скобках — обозначения синтаксиса, не буквальные команды. Примеры вызова ниже документированы upstream, но здесь не запускались.

### Hermes

[Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) документирует два проектных корня: `.hermes/skills` и `.agents/skills`. Корень проекта — ближайший предок с `.git`; worktree и submodule учитываются. Для загрузки требуется явное доверие через `hermes skills trust`. Копирование файлов само по себе не даёт доверия и не делает навык доступным.

Пользовательский путь — `skills` внутри активного `HERMES_HOME`, по умолчанию `~/.hermes/skills`. Для [именованного профиля](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) обычный путь — `~/.hermes/profiles/<name>/skills`. Установщик должен учитывать выбранный профиль, не писать в default молча.

Навыки обнаруживаются с вложенными категориями. Приоритет: проектные → локальные → `skills.create_dir` → `skills.external_dirs`. Пользовательский `~/.agents/skills` можно подключить через `skills.external_dirs`; нельзя считать его безусловно сканируемым корнем Hermes.

Интерфейс агента: `skills_list`, `skill_view`, `skill_manage`. Для чтения используйте `skill_view(name)` и `skill_view(name, file_path)`; slash-вызов — `/<skill-name> [запрос]`. Не переносите сюда Claude-инструмент `Skill` или Pi-синтаксис `/skill:name`.

### OpenClaw

В [Loading order](https://docs.openclaw.ai/tools/skills) основной каталог — `<workspace>/skills`; также поддержан `<workspace>/.agents/skills`. Workspace задаётся агенту OpenClaw: произвольный checkout не становится им автоматически. Установщику нужен явно выбранный workspace.

Managed/local каталог — `<state-dir>/skills`, обычно `~/.openclaw/skills`. Учитывайте `OPENCLAW_STATE_DIR` и профиль. Это общий каталог агентов данного state, а не личная библиотека оператора shared Gateway. Последней управляют отдельные интерфейсы; её внутреннее хранилище нельзя заполнять прямым копированием.

Приоритет начинается с workspace `skills`, workspace `.agents/skills`, пользовательского `~/.agents/skills`, managed/local skills. Домашний `.agents/skills` участвует только при default state. Обнаружение `SKILL.md` рекурсивное до шести уровней.

Текущая документация поддерживает `$<skill-command-name>` внутри запроса и ведущую `/<skill-command-name>`. Используйте зарегистрированное имя: оно происходит из `name` и может нормализоваться хостом. Действуют `user-invocable`, allowlist и другие ограничения. Для discovery документированы условно доступные `skills_search` и `skills_read`. Из [инструментов OpenClaw](https://docs.openclaw.ai/tools) для адаптации полезны `read`, `write`, `edit`, `exec`, `web_search`, `web_fetch`. Это не названия инструментов Hermes.

### Claude Code

Официальная [страница Skills](https://code.claude.com/docs/en/skills) задаёт пользовательский `~/.claude/skills/<skill-name>/SKILL.md` и проектный `.claude/skills/<skill-name>/SKILL.md`. Поддержаны вложенные проектные области, enterprise и plugins; старый `.claude/commands` совместим, но не нужен как цель нового установщика. Для нестандартной конфигурации нужно учитывать `CLAUDE_CONFIG_DIR`.

Явный вызов — `/<skill-name> [запрос]`; автоматический выбор опирается на `description`. `disable-model-invocation: true` запрещает автоматический выбор, `user-invocable: false` скрывает пользовательскую команду. Расширения frontmatter Claude Code не следует считать переносимыми без проверки другого хоста.

[Tools reference](https://code.claude.com/docs/en/tools-reference) подтверждает `Skill`, `Read`, `Write`, `Edit`, `Bash`. Регистр значим. Текущая справка отмечает, что `Grep` и `Glob` по умолчанию отсутствуют на macOS/Linux/WSL; адаптация не должна безусловно требовать их.

### Codex

Официальный адрес [Codex Skills](https://developers.openai.com/codex/skills/) при проверке перенаправил на [Build skills](https://learn.chatgpt.com/docs/build-skills). В разделе **Where Codex loads local skills** указаны `.agents/skills` от текущего каталога до корня репозитория и `$HOME/.agents/skills` для пользователя. Также есть `/etc/codex/skills` и bundled system skills.

Для нового установщика выбирайте **`~/.agents/skills`, не `~/.codex/skills`**. Старые примеры установки не заменяют текущую таблицу discovery. Файл `~/.codex/config.toml` остаётся файлом настроек; из этого не следует другой корень навыков. Symlink-каталоги навыков поддержаны.

Codex CLI/IDE используют `$<skill-name>` или выбор через `/skills`; `@skill` на той же странице относится к ChatGPT, не к Codex CLI. Необязательный `agents/openai.yaml` задаёт метаданные и политику, включая `allow_implicit_invocation`.

В исходниках OpenAI подтверждены [`exec_command` и `write_stdin`](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/handlers/shell_spec.rs), а также [`apply_patch`](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/handlers/apply_patch_spec.rs). Набор зависит от модели и режима. Не изобретайте для Codex универсальный `Skill` или обязательный `read_file`: полагайтесь на фактические схемы инструментов сессии.

### Pi — coding-agent из badlogic/pi-mono

Запрошенный адрес [`badlogic/pi-mono`](https://github.com/badlogic/pi-mono) при проверке перенаправил в [`earendil-works/pi`](https://github.com/earendil-works/pi). Проверены документы `packages/coding-agent` именно этого проекта, не другого продукта с названием Pi.

[Configuration](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md) задаёт `.pi/skills` в рабочем каталоге и `<agent-dir>/skills`, где agent directory по умолчанию `~/.pi/agent`. Переопределения — `PI_CODING_AGENT_DIR` или SDK `agentDir`. Проектная конфигурация загружается после project trust.

[Skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) также поддерживает `~/.agents/skills` и проектные `.agents/skills` по предкам до repository root. Каталоги с `SKILL.md` обнаруживаются рекурсивно. Явный вызов — `/skill:<skill-name> [запрос]`; после изменений — `/reload`. `enableSkillCommands` управляет показом в интерактивном списке, но вручную введённая `/skill:name` продолжает работать.

По [Settings](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md) стандартный набор — `read`, `bash`, `edit`, `write`. Другие встроенные инструменты существуют, но не обязательно включены. Инструкции читаются через файловый `read`, отдельный `skill_view` не требуется.

### Oh My Pi — отдельный форк

Канонический репозиторий — [`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi), сайт — `omp.sh`, команда — `omp`, пакет — `@oh-my-pi/pi-coding-agent`. README прямо связывает продукт с форком Pi. Не смешивайте native `.omp` с `.pi` upstream.

[Configuration Discovery](https://github.com/can1357/oh-my-pi/blob/main/docs/config-usage.md) и [native provider](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/discovery/builtin.ts) подтверждают `.omp/skills` по предкам рабочего каталога и `<getAgentDir()>/skills`, обычно `~/.omp/agent/skills`. Обычный путь именованного профиля — `~/.omp/profiles/<name>/agent/skills`; документированы дополнительные environment/XDG overrides. Выбранный профиль нужно учитывать отдельно от default.

[Skills](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md) описывает **нерекурсивное** обнаружение `<skills-root>/<skill-name>/SKILL.md`. Макет `skills/group/name/SKILL.md` для native provider не подходит. Устанавливайте семь отдельных каталогов прямо в корень skills. Native provider имеет приоритет 100; foreign user providers требуют opt-in, поэтому нельзя рассчитывать на чужие пользовательские корни как замену `.omp`.

Модель читает инструкции инструментом `read` по `skill://<skill-name>` и ресурсы по `skill://<skill-name>/<relative-path>`. Явная команда — `/skill:<skill-name>`, если `skills.enableSkillCommands` включён. Документирован `omp skill list --json` для просмотра. В README перечислены `read`, `write`, `edit`, `bash`, `grep`, `glob`, `web_search`; `manage_skill` работает с managed skills и не заменяет чтение опубликованного пакета.

## Граница совместимости и исполняемой проверки

Общий формат `SKILL.md` не делает названия инструментов, slash-синтаксис, frontmatter-расширения или права доступа одинаковыми. Адаптация должна ссылаться на инструменты своего хоста, а при их отсутствии — явно останавливать соответствующий шаг. Обнаружение навыка не доказывает выполнение сценария, наличие зависимостей или качество исследовательского результата.

Установщик должен:

- разрешать только один явно выбранный хост и scope за операцию, учитывать overrides и профиль;
- сохранять каталоги ресурсов навыка, а для Oh My Pi — плоский уровень каталогов;
- не выдавать доверие проекту, не включать providers и не менять tool policy без отдельного согласия;
- после копирования проверять файлы, но не называть это runtime-тестом;
- для статуса «проверено в работе» отдельно показать обнаружение в целевой оболочке, загрузку инструкции, чтение вложенного ресурса и реальное выполнение выбранного сценария.

На этой стадии подтверждены только официальные пути, правила обнаружения и интерфейсы. Установки, входа в аккаунты, изменения конфигурации и запуска шести оболочек не было.
