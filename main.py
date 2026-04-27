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
    from aiogram.client.default import DefaultBotProperties
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

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
    from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
    import hashlib as _hs

    @dp.inline_query()
    async def inline_player_search(query: InlineQuery):
        q = query.query
        if not q.startswith("search:"):
            await query.answer([], cache_time=1)
            return
        try:
            parts      = q.split(" ", 1)
            meta_parts = parts[0].split(":")
            slot       = meta_parts[1] if len(meta_parts) > 1 else ""
            pos        = meta_parts[2] if len(meta_parts) > 2 else "GK"
            term       = parts[1].strip().lower() if len(parts) > 1 else ""

            from players import get_players_by_position, fmt_price
            players = get_players_by_position(pos)
            if term:
                players = [p for p in players
                           if term in p["name"].lower() or term in p["team"].lower()]
            players = sorted(players, key=lambda p: -p["price"])[:20]

            articles = []
            for p in players:
                articles.append(InlineQueryResultArticle(
                    id=_hs.md5((slot + p["id"]).encode()).hexdigest(),
                    title=p["name"],
                    description=p["team"] + " — " + fmt_price(p["price"]),
                    input_message_content=InputTextMessageContent(
                        message_text="🔍 " + p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"])
                    ),
                    reply_markup=__import__("aiogram").types.InlineKeyboardMarkup(
                        inline_keyboard=[[
                            __import__("aiogram").types.InlineKeyboardButton(
                                text="✅ Add to squad",
                                callback_data="pick:" + slot + ":" + p["id"]
                            )
                        ]]
                    )
                ))
            await query.answer(articles, cache_time=5, is_personal=True)
        except Exception as e:
            logger.error("inline search: %s", e)
            await query.answer([], cache_time=1)

    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "inline_query"])


if __name__ == "__main__":
    asyncio.run(main())
