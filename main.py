import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import sheets
import registration
import squad
import transfers
import admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(registration.router)
    dp.include_router(squad.router)
    dp.include_router(transfers.router)
    dp.include_router(admin.router)

    logger.info("Initializing Supabase DB...")
    try:
        await sheets.init_db()
    except Exception as e:
        logger.error("DB init failed: %s — continuing anyway.", e)

    # Start points scheduler as background task
    if config.API_FOOTBALL_KEY:
        from scheduler import run_scheduler
        asyncio.create_task(run_scheduler(bot))
        logger.info("Points scheduler started.")
    else:
        logger.warning("API_FOOTBALL_KEY not set — points scheduler disabled.")

    logger.info("Bot starting...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
