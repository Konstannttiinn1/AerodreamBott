# Aerodream Telegram Bot

Telegram-бот для aerodream.spb.ru на базе aiogram 3.x.

## Быстрый старт

1. Создайте файл `.env` по примеру:

```bash
cp .env.example .env
```

2. Заполните переменные в `.env`.

3. Запустите в Docker:

```bash
docker compose up -d --build
```

## Логи

```bash
docker compose logs -f bot
```

## Проверка основных сценариев

1. `/start` — открыть пользовательское меню.
2. `/admin` — открыть админское меню (только ADMIN_IDS).
3. В админском меню выберите **📣 Рассылка** и пройдите мастер.

## Структура

```
app/
  handlers/
  keyboards/
  services/
  db/
content.yaml
```
