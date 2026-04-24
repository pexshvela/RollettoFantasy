"""
main.py — Bot entry point.
Registers all routers and starts the scheduler.
"""
import asyncio
import logging
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.enums import ParseMode

    import sheets
    import players as pl_module
    from scheduler import run_scheduler

    # Import routers
    from registration import router as reg_router
    from squad       import router as squad_router
    from transfers   import router as transfer_router
    from stats       import router as stats_router
    from admin       import router as admin_router

    logger.info("Bot starting...")

    # Init DB
    await sheets.init_db()

    # Set active tournament
    tournament = await sheets.get_tournament()
    pl_module.set_active_tournament(tournament)
    logger.info("Active tournament: %s", tournament.upper())

    bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp  = Dispatcher(storage=MemoryStorage())

    # Register routers — order matters
    dp.include_router(admin_router)
    dp.include_router(reg_router)
    dp.include_router(squad_router)
    dp.include_router(transfer_router)
    dp.include_router(stats_router)

    # Start scheduler in background
    asyncio.create_task(run_scheduler(bot))

    logger.info("Start polling")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
