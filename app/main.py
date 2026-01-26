from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import Config
from app.db.db import Database
from app.handlers.user import router as user_router
from app.handlers.admin import router as admin_router
from app.handlers.broadcast import router as broadcast_router
from app.services.content import load_content
from app.services.automation import automation_loop


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = Config.from_env()
    db = Database(config.database_path)
    await db.init(config.enable_automation)
    content = load_content("content.yaml")

    bot = Bot(config.bot_token)
    dp = Dispatcher()
    # Admin routers must be registered before the user router to avoid fallback intercepting commands.
    dp.include_router(admin_router)
    dp.include_router(broadcast_router)
    dp.include_router(user_router)

    asyncio.create_task(automation_loop(bot, db, config.timezone))
    await dp.start_polling(bot, config=config, db=db, content=content)


if __name__ == "__main__":
    asyncio.run(main())
