# Прототип: Фактчекинг драфта текста (FastAPI)

Минимальное веб‑приложение, которое:
- принимает драфт текста;
- извлекает основные факты/утверждения с помощью OpenAI;
- ищет подтверждения в интернете через SearchAPI.io (`https://www.searchapi.io/`);
- формирует отчет по фактчекингу (поддержано/опровергнуто/неопределенно) с цитатами.

## Быстрый старт (локально)

1) Python 3.10+

2) Переменные окружения (или `.env`):

```
cp .env.example .env
# отредактируйте .env: OPENAI_API_KEY, SEARCHAPI_KEY
```

3) Установка:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4) Запуск:

```
uvicorn app.main:app --reload --port 8000
```

5) Интерфейс: http://127.0.0.1:8000/

## Деплой (Docker)

Сборка и запуск:

```
docker build -t factcheck-proto .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e SEARCHAPI_KEY=sa_live_... \
  -e SEARCHAPI_RESULTS=5 \
  factcheck-proto
```

Откройте: http://127.0.0.1:8000/

## Деплой (Render.com)

Вариант 1 — через репозиторий:
- Подключите репозиторий к Render, выберите "Blueprint" и `render.yaml`
- Установите `OPENAI_API_KEY`, `SEARCHAPI_KEY` в Render → Environment

Вариант 2 — вручную как Docker Web Service:
- New → Web Service → from repo → Docker
- Переменные окружения:
  - `OPENAI_API_KEY`
  - `SEARCHAPI_KEY`
  - `SEARCHAPI_RESULTS` (опц.)
- Порт: `8000` (Render сам передаст `PORT` контейнеру)

## Переменные окружения

- `OPENAI_API_KEY`
- `SEARCHAPI_KEY`
- `SEARCHAPI_RESULTS` (по умолчанию `5`)

## Примечания

- Проект — прототип. Возможны ошибки и лимиты API.
- Издержки: OpenAI и SearchAPI.io тарифицируются, используйте с ограничениями.