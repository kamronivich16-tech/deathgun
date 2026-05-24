import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
import db
from handlers import router
from middlewares import BanMiddleware

async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init_db()

    bot = Bot(token=config.TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(router)
    dp.message.middleware(BanMiddleware())
    dp.callback_query.middleware(BanMiddleware())

    print("Bot started and ready!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
