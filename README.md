# FactCheck Prototype

Простой прототип веб‑приложения для фактчекинга текста:
- LLM (OpenAI) выделяет проверяемые факты
- Поиск по сети через searchapi.io
- Рейтинг тезисов с цитатами источников

## Быстрый старт

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Создайте `.env` на основе `.env.example` и заполните ключи:

- `OPENAI_API_KEY` — ключ OpenAI
- `SEARCHAPI_API_KEY` — ключ searchapi.io

3. Запустите сервер:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Откройте браузер: `http://localhost:8000`

## Структура

- `app/main.py` — FastAPI, эндпоинт `/api/factcheck`
- `app/services/llm.py` — извлечение фактов и вынесение вердикта (OpenAI)
- `app/services/search.py` — поиск через searchapi.io
- `public/*` — статический фронтенд

## Примечания
- Прототип. Без сложной обработки ошибок, логирования и кеша.
- Для продакшена рекомендованы: ограничение токенов, очереди, ретраи, нормализация источников.