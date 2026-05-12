from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import db

class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        user = await db.get_user(user_id)
        if user and user[4] == 1: # Столбец is_banned
            if isinstance(event, Message):
                await event.answer("❌ Вы заблокированы администратором.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Вы заблокированы.", show_alert=True)
            return
        return await handler(event, data)
