import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import db
import config

router = Router()

class TextStartsWith(BaseFilter):
    def __init__(self, *prefixes: str):
        self.prefixes = tuple(p.lower() for p in prefixes)

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        return message.text.lower().startswith(self.prefixes)

class GameStates(StatesGroup):
    waiting_for_bet = State()
    waiting_for_game = State()

class AdminStates(StatesGroup):
    waiting_for_id_give = State()
    waiting_for_amount_give = State()
    waiting_for_id_take = State()
    waiting_for_amount_take = State()
    waiting_for_id_ban = State()
    waiting_for_id_unban = State()
    waiting_for_broadcast = State()
    waiting_for_nft_user_id = State()
    waiting_for_nft_name = State()

def get_main_kb(user_id):
    kb = [
        [KeyboardButton(text="📱 Меню"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🎮 Игры"), KeyboardButton(text="🏆 Топ")]
    ]
    if user_id in config.ADMINS:
        kb.append([KeyboardButton(text="⚙️ Админка")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_help_kb():
    buttons = [
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="menu_0")],
        [InlineKeyboardButton(text="🌐 Основное", callback_data="menu_1")],
        [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_2")],
        [InlineKeyboardButton(text="💼 Заработок", callback_data="menu_3")],
        [InlineKeyboardButton(text="📊 NFT", callback_data="menu_4")],
        [InlineKeyboardButton(text="💰 Донат", callback_data="menu_5")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_6")],
        [InlineKeyboardButton(text="💡 Другое", callback_data="menu_7")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

HELP_TEXT = """Игрок, разделы команд:

ℹ️ 0. О боте
🌐 1. Основные команды
🎮 2. Игры
💼 3. Заработок
📊 4. Биржа
💰 5. Меню доната
⚙️ 6. Настройки профиля
💡 7. Другое

❓ Чтобы перейти в определенный раздел, напишите:
«Помощь [номер раздела]» или используйте кнопки ниже"""

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
    # Реферальная система
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        ref_val = int(args[1])
        if ref_val != message.from_user.id:
            referrer_id = ref_val
    
    is_new = await db.add_user(message.from_user.id, message.from_user.username, referrer_id)
    
    if is_new and referrer_id:
        # Выдаем 10 000 монет пригласителю
        await db.update_balance(referrer_id, 10000)
        try:
            await message.bot.send_message(
                chat_id=referrer_id,
                text=f"👥 По вашей реферальной ссылке зарегистрировался новый игрок: @{message.from_user.username or 'без юзера'}\n💰 Вам зачислено `+10,000` монет!"
            )
        except Exception:
            pass
            
    await message.answer(
        "👋 **Добро пожаловать в H8E1 Clone!**\n\nВыбери раздел ниже для ознакомления:",
        reply_markup=get_main_kb(message.from_user.id)
    )
    await message.answer(HELP_TEXT, reply_markup=get_help_kb())

@router.message(F.text == "📱 Меню")
async def menu_msg(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=get_help_kb())

@router.message(F.text == "👤 Профиль")
async def profile_msg(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    
    # Получаем экипированные NFT
    user_nfts = await db.get_user_nfts(message.from_user.id)
    equipped = {nft[5]: nft for nft in user_nfts if nft[4] == 1} # nft[5] - position, nft[4] - is_equipped
    
    equipped_text = ""
    for pos in range(1, 7):
        if pos in equipped:
            nft = equipped[pos]
            equipped_text += f"{pos}. 🎁 **{nft[2]}** (ID: `{nft[0]}`) — Ур. `{nft[3]}`\n"
        else:
            equipped_text += f"{pos}. 📦 *Пусто*\n"
            
    text = (
        f"👤 **Профиль:**\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"💰 Баланс: `{user[2]:,}` монет\n"
        f"💎 TON: `{user[6]:.2f}` TON\n\n"
        f"📌 **Закрепленные подарки:**\n"
        f"{equipped_text}\n"
        f"👥 **Реферальная система:**\n"
        f"Приглашай друзей и получай `+10,000` монет за каждого нового игрока!\n\n"
        f"🔗 **Твоя реферальная ссылка:**\n`{ref_link}`"
    )
    await message.answer(text)

@router.message(F.text == "🏆 Топ")
async def top_msg(message: Message, state: FSMContext):
    await state.clear()
    top = await db.get_top_users()
    text = "🏆 **Рейтинг самых богатых:**\n\n"
    for i, (username, balance) in enumerate(top, 1):
        text += f"{i}. {username} — `{balance:,}`\n"
    await message.answer(text)

# --- ИГРЫ ---

@router.message(F.text == "🎮 Игры")
async def games_msg(message: Message, state: FSMContext):
    await state.clear()
    buttons = [
        [InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice"), InlineKeyboardButton(text="🎰 Слоты", callback_data="game_slots")],
        [InlineKeyboardButton(text="🪙 Монетка (50/50)", callback_data="game_coin")]
    ]
    await message.answer("🎮 **Выбери игру:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("game_"))
async def game_start(callback: CallbackQuery, state: FSMContext):
    game_type = callback.data.split("_")[1]
    user = await db.get_user(callback.from_user.id)
    
    if user[2] <= 0:
        return await callback.answer("❌ У вас нет денег для игры!", show_alert=True)
    
    await state.update_data(game_type=game_type)
    await state.set_state(GameStates.waiting_for_bet)
    
    kb = [
        [InlineKeyboardButton(text="100", callback_data="bet_100"), InlineKeyboardButton(text="500", callback_data="bet_500")],
        [InlineKeyboardButton(text="1000", callback_data="bet_1000"), InlineKeyboardButton(text="Все", callback_data="bet_all")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back")]
    ]
    
    game_names = {"dice": "🎲 Кости", "slots": "🎰 Слоты", "coin": "🪙 Монетка"}
    await callback.message.edit_text(
        f"🎮 Игра: **{game_names[game_type]}**\n💰 Баланс: `{user[2]:,}`\n\n✍️ **Напиши сумму ставки или выбери кнопку:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("bet_"), GameStates.waiting_for_bet)
async def bet_callback(callback: CallbackQuery, state: FSMContext):
    bet_val = callback.data.split("_")[1]
    user = await db.get_user(callback.from_user.id)
    
    if bet_val == "all":
        bet = user[2]
    else:
        bet = int(bet_val)
        
    if bet > user[2]:
        return await callback.answer("❌ Недостаточно средств!", show_alert=True)
    
    await process_game(callback.message, callback.from_user.id, bet, state)

@router.message(GameStates.waiting_for_bet)
async def bet_text(message: Message, state: FSMContext):
    if not message.text.isdigit():
        # Если нажата кнопка меню, сбрасываем FSM
        if message.text in ["📱 Меню", "👤 Профиль", "🎮 Игры", "🏆 Топ", "⚙️ Админка"]:
            await state.clear()
            # Перенаправляем на нужный обработчик
            if message.text == "📱 Меню": await menu_msg(message, state)
            elif message.text == "👤 Профиль": await profile_msg(message, state)
            elif message.text == "🎮 Игры": await games_msg(message, state)
            elif message.text == "🏆 Топ": await top_msg(message, state)
            elif message.text == "⚙️ Админка": await admin_panel(message, state)
            return
        return await message.answer("❌ Введите число!")
    
    bet = int(message.text)
    user = await db.get_user(message.from_user.id)
    if bet <= 0 or bet > user[2]:
        return await message.answer("❌ Ошибка в сумме ставки!")
    
    await process_game(message, message.from_user.id, bet, state)

async def process_game(msg, user_id, bet, state):
    data = await state.get_data()
    game_type = data['game_type']
    await state.clear()
    
    if game_type == "dice":
        m = await msg.answer_dice(emoji="🎲")
        await asyncio.sleep(3)
        if m.dice.value >= 4:
            mult = random.choice([1.5, 2.0, 3.0])
            win = int(bet * mult)
            await db.update_balance(user_id, win - bet)
            await msg.answer(f"🎉 **Победа!**\n🔥 Множитель: `x{mult}`\n💰 Выигрыш: `+{win:,}`")
        else:
            await db.update_balance(user_id, -bet)
            await msg.answer(f"🌑 **Проигрыш!**\n💸 Потеряно: `-{bet:,}`")
            
    elif game_type == "slots":
        m = await msg.answer_dice(emoji="🎰")
        await asyncio.sleep(3)
        # Упрощенная логика слотов aiogram
        # 1, 22, 43, 64 - джекпоты
        if m.dice.value in [1, 22, 43, 64]:
            mult = random.choice([5.0, 10.0, 50.0])
            win = int(bet * mult)
            await db.update_balance(user_id, win - bet)
            await msg.answer(f"💎 **ДЖЕКПОТ!**\n🔥 Множитель: `x{mult}`\n💰 Выигрыш: `+{win:,}`")
        else:
            await db.update_balance(user_id, -bet)
            await msg.answer(f"🌑 **Мимо...**\n💸 Потеряно: `-{bet:,}`")
            
    elif game_type == "coin":
        res = random.choice(["heads", "tails"])
        if res == "heads":
            mult = random.choice([1.5, 2.0, 2.5, 3.0, 5.0])
            win = int(bet * mult)
            await db.update_balance(user_id, win - bet)
            await msg.answer(f"🌕 **ОРЕЛ!**\n🔥 Множитель: `x{mult}`\n💰 Выигрыш: `+{win:,}`")
        else:
            await db.update_balance(user_id, -bet)
            await msg.answer(f"🌑 **РЕШКА...**\n🔥 Множитель: `x0`\n💸 Проиграно: `-{bet:,}`")

# --- РАЗДЕЛЫ МЕНЮ ---

@router.callback_query(F.data.startswith("menu_"))
async def handle_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    menu_id = callback.data.split("_")[1]
    
    if menu_id == "back":
        return await callback.message.edit_text("ℹ️ **Разделы меню:**", reply_markup=get_help_kb())

    texts = {
        "0": "ℹ️ **О боте**\n\nЭто полноценный клон игрового бота H8E1.\nЗдесь вы можете играть, зарабатывать монеты и соревноваться в топе!",
        "1": "🌐 **Основные команды**\n\n/start — Главное меню\n/profile — Ваш профиль\n/top — Список богачей\n/give ID сумма — Выдать монеты (админ)",
        "2": "🎮 **Игровой процесс**\n\nВ нашем боте есть 3 вида игр:\n1. 🎲 Кости\n2. 🎰 Слоты\n3. 🪙 Монетка\n\nВсе игры имеют систему случайных множителей до x50!",
        "3": "💸 **Заработок**\n\n🎁 Получайте бесплатные монеты раз в 24 часа.\n\n👥 **Реферальная программа:**\nПриглашайте друзей и получайте `+10,000` монет за каждого нового игрока!\nВаша ссылка для приглашения находится в разделе 👤 **Профиль**.",
        "4": """Игрок, команды для биржи:

🛍 Маркет — торговая площадка активов
🎁 Мои подарки — посмотреть список своих подарков
📈 Мои активы — посмотреть список своих активов
🆙 Подарок улучшить [название подарка] — улучшить подарок
🗄 Передать [id/ссылка/@user] [название подарка] [ID подарка] — передать свой подарок другому игроку
🤝 Сделка [id/ссылка/@user] [название подарка] [ID подарка] [цена (от 100 TON)] — предложить покупку NFT подарка
📄 Сделки — список активных сделок
✨ Стоимость улучшения — посмотреть стоимость улучшения подарка
🕶 Надеть [название подарка] [ID подарка] — надеть подарок
📌 Закрепить [название подарка] [ID подарка] [позиция (1-6)] — закрепить NFT подарок в профиле
✂️ Открепить [позиция (1-6)] — открепить NFT подарок из профиля
🔍 Сподарок [название подарка] [ID подарка] — информация об NFT подарке
💹 Курс — посмотреть курс TON и Искр""",
        "5": "💎 **Донат**\n\nПоддержите проект и получите монеты! Для покупки свяжитесь с администратором."
    }
    
    kb = []
    if menu_id == "3":
        kb.append([InlineKeyboardButton(text="🎁 Получить бонус", callback_data="get_bonus")])
    elif menu_id == "4":
        kb.append([InlineKeyboardButton(text="🛍 Маркет", callback_data="nft_market"), InlineKeyboardButton(text="🎁 Мои подарки", callback_data="nft_my")])
    elif menu_id == "5":
        kb.append([InlineKeyboardButton(text="💎 Купить монеты", url=f"tg://user?id={config.ADMINS[0]}")])
        
    kb.append([InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back")])
    await callback.message.edit_text(texts.get(menu_id, "Раздел в разработке"), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.lower().startswith("помощь"))
async def help_number_cmd(message: Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer(HELP_TEXT, reply_markup=get_help_kb())
    
    num = parts[1]
    # Имитируем нажатие кнопки
    class MockCallback:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
        async def answer(self, text=None, show_alert=False): pass

    # Просто вызываем handle_menu с фейковым callback для логики
    # Но проще просто вынести логику текстов в отдельную функцию. 
    # Для простоты сейчас просто ответим текстом.
    texts = {
        "0": "ℹ️ **О боте**\n\nЭто полноценный клон игрового бота H8E1.",
        "1": "🌐 **Основные команды**\n\n/start — Главное меню\n/profile — Ваш профиль\n/top — Список богачей",
        "2": "🎮 **Игровой процесс**\n\nВ нашем боте есть 3 вида игр:\n1. 🎲 Кости\n2. 🎰 Слоты\n3. 🪙 Монетка",
        "3": "💸 **Заработок**\n\nПолучайте бонусы раз в 24 часа и приглашайте друзей (10,000 монет за каждого нового игрока)!",
        "4": "📊 **Биржа / NFT**\n\nИспользуйте команды со скриншота для управления активами.",
        "5": "💰 **Меню доната**\n\nСвяжитесь с админом для покупки монет.",
        "6": "⚙️ **Настройки профиля**\n\nРаздел в разработке.",
        "7": "💡 **Другое**\n\nДополнительная информация."
    }
    await message.answer(texts.get(num, "Раздел не найден."), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back")]]))

@router.callback_query(F.data == "get_bonus")
async def bonus_callback(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    last_bonus = user[3]
    
    if last_bonus:
        last_time = datetime.fromisoformat(last_bonus)
        if datetime.now() < last_time + timedelta(hours=24):
            diff = (last_time + timedelta(hours=24)) - datetime.now()
            hours, remainder = divmod(int(diff.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return await callback.answer(f"⏳ Бонус доступен через {hours}ч {minutes}м!", show_alert=True)
            
    reward = random.randint(1000, 5000)
    await db.update_balance(callback.from_user.id, reward)
    await db.update_last_bonus(callback.from_user.id, datetime.now().isoformat())
    await callback.answer(f"🎁 Вы получили {reward:,} монет!", show_alert=True)

# --- АДМИНКА ---

@router.message(F.text == "⚙️ Админка")
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    await state.clear()
    kb = [
        [InlineKeyboardButton(text="➕ Монеты", callback_data="adm_give"), InlineKeyboardButton(text="➖ Монеты", callback_data="adm_take")],
        [InlineKeyboardButton(text="🔨 Бан", callback_data="adm_ban"), InlineKeyboardButton(text="🕊 Разбан", callback_data="adm_unban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast"), InlineKeyboardButton(text="🎁 Создать NFT", callback_data="adm_mint")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")]
    ]
    await message.answer("⚙️ **Панель администратора:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("adm_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS: return
    act = callback.data.split("_")[1]
    
    if act == "stats":
        users = await db.get_all_users()
        total_balance = sum(u[2] for u in users)
        banned = sum(1 for u in users if u[4] == 1)
        await callback.message.answer(f"📊 **Статистика:**\n\n👥 Всего: `{len(users)}` чел.\n💰 В обороте: `{total_balance:,}`\n🔨 В бане: `{banned}`")
        await callback.answer()
        return

    if act == "broadcast":
        await state.set_state(AdminStates.waiting_for_broadcast)
        await callback.message.answer("📢 **Введите текст сообщения для рассылки:**")
        await callback.answer()
        return

    if act == "mint":
        await state.set_state(AdminStates.waiting_for_nft_user_id)
        await callback.message.answer("🎁 **Введите ID или username игрока, которому хотите создать NFT:**")
        await callback.answer()
        return

    await state.update_data(admin_act=act)
    await state.set_state(AdminStates.waiting_for_id_give if act == "give" else AdminStates.waiting_for_id_take if act == "take" else AdminStates.waiting_for_id_ban if act == "ban" else AdminStates.waiting_for_id_unban)
    await callback.message.answer("✍️ **Введите ID пользователя:**")
    await callback.answer()

@router.message(AdminStates.waiting_for_id_give)
@router.message(AdminStates.waiting_for_id_take)
@router.message(AdminStates.waiting_for_id_ban)
@router.message(AdminStates.waiting_for_id_unban)
async def admin_id_input(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ ID должен быть числом!")
    target_id = int(message.text)
    data = await state.get_data()
    act = data['admin_act']
    
    if act in ["ban", "unban"]:
        await db.set_ban(target_id, 1 if act == "ban" else 0)
        await state.clear()
        await message.answer(f"✅ Пользователь `{target_id}` {'забанен' if act == 'ban' else 'разбанен'}.")
    else:
        await state.update_data(target_id=target_id)
        await state.set_state(AdminStates.waiting_for_amount_give if act == "give" else AdminStates.waiting_for_amount_take)
        await message.answer("✍️ **Введите сумму:**")

@router.message(AdminStates.waiting_for_amount_give)
@router.message(AdminStates.waiting_for_amount_take)
async def admin_amount_input(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Введите число!")
    amount = int(message.text)
    if amount > 10**15:
        return await message.answer("❌ Сумма слишком большая!")
    data = await state.get_data()
    target_id = data['target_id']
    act = data['admin_act']
    
    if act == "take": amount = -amount
    await db.update_balance(target_id, amount)
    await state.clear()
    await message.answer(f"✅ Успешно! Сумма: `{abs(amount):,}`")

@router.message(AdminStates.waiting_for_broadcast)
async def admin_broadcast_input(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    broadcast_text = message.text
    await state.clear()
    
    users = await db.get_all_users()
    await message.answer(f"📢 Запущена рассылка на `{len(users)}` пользователей...")
    
    success = 0
    fail = 0
    for u in users:
        user_id = u[0]
        try:
            await message.bot.send_message(chat_id=user_id, text=broadcast_text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
            
    await message.answer(f"📢 **Рассылка завершена!**\n\n✅ Успешно доставлено: `{success}`\n❌ Ошибок: `{fail}`")

@router.message(AdminStates.waiting_for_nft_user_id)
async def admin_nft_user_input(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    
    target_user = await db.resolve_user(message.text)
    if not target_user:
        return await message.answer("❌ Пользователь не найден в базе данных! Попробуйте ввести точный числовой ID.")
        
    await state.update_data(target_user_id=target_user[0])
    await state.set_state(AdminStates.waiting_for_nft_name)
    
    kb = [
        [InlineKeyboardButton(text="👑 Корона", callback_data="mintname_👑 Корона"), InlineKeyboardButton(text="💎 Алмаз", callback_data="mintname_💎 Алмаз")],
        [InlineKeyboardButton(text="🚗 Ламба", callback_data="mintname_🚗 Ламба"), InlineKeyboardButton(text="🍕 Пицца", callback_data="mintname_🍕 Пицца")],
        [InlineKeyboardButton(text="🌟 Звезда", callback_data="mintname_🌟 Звезда"), InlineKeyboardButton(text="⚡️ Молния", callback_data="mintname_⚡️ Молния")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_back")]
    ]
    await message.answer(
        f"🎁 Игрок найден: **{target_user[1] or 'User'}** (ID: `{target_user[0]}`)\n\n"
        f"✍️ **Выберите название подарка ниже или введите своё текстом:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("mintname_"), AdminStates.waiting_for_nft_name)
async def admin_nft_name_callback(callback: CallbackQuery, state: FSMContext):
    nft_name = callback.data.split("_")[1]
    await execute_mint(callback.message, state, nft_name)
    await callback.answer()

@router.message(AdminStates.waiting_for_nft_name)
async def admin_nft_name_input(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    nft_name = message.text.strip()
    if not nft_name:
        return await message.answer("❌ Название не должно быть пустым!")
    await execute_mint(message, state, nft_name)

async def execute_mint(msg, state, nft_name):
    data = await state.get_data()
    target_user_id = data['target_user_id']
    await state.clear()
    
    await db.add_nft(target_user_id, nft_name)
    await msg.answer(f"✅ NFT подарок **{nft_name}** успешно создан для пользователя `{target_user_id}`!")
    
    try:
        await msg.bot.send_message(
            chat_id=target_user_id,
            text=f"🎁 Администратор выдал вам новый NFT подарок: **{nft_name}**!\n"
                 f"Посмотреть свои подарки можно с помощью кнопки 🎁 **Мои подарки**."
        )
    except Exception:
        pass

@router.message(Command("give"))
async def cmd_give(message: Message):
    if message.from_user.id not in config.ADMINS: return
    args = message.text.split()
    if len(args) < 3: return await message.answer("ℹ️ `/give ID сумма`")
    try:
        target_id = int(args[1])
        amount = int(args[2])
        if abs(amount) > 10**15 or abs(target_id) > 10**15:
            raise ValueError
        await db.update_balance(target_id, amount)
        await message.answer("✅ Выдано!")
    except ValueError:
        await message.answer("❌ Неверные значения или числа слишком большие!")

@router.message(F.text == "💹 Курс")
async def course_cmd(message: Message):
    await message.answer("💹 **Актуальный курс:**\n\n💎 1 TON = `450,000` Искр\n🔥 1 Искра = `0.0000022` TON")

MARKET_ITEMS = {
    "crown": {"name": "👑 Корона", "coins": 500000, "ton": 1.0},
    "diamond": {"name": "💎 Алмаз", "coins": 200000, "ton": 0.5},
    "lambo": {"name": "🚗 Ламба", "coins": 100000, "ton": 0.25},
    "pizza": {"name": "🍕 Пицца", "coins": 50000, "ton": 0.1},
    "star": {"name": "🌟 Звезда", "coins": 10000, "ton": 0.05},
    "lightning": {"name": "⚡️ Молния", "coins": 5000, "ton": 0.02},
}

@router.message(F.text == "🛍 Маркет")
async def market_cmd(message: Message):
    kb = []
    for item_id, item_data in MARKET_ITEMS.items():
        kb.append([InlineKeyboardButton(text=f"{item_data['name']} — {item_data['coins']:,} монет / {item_data['ton']} TON", callback_data=f"market_buy_{item_id}")])
    
    await message.answer("🛍 **Официальный Маркет Подарков**\nЗдесь вы можете приобрести NFT подарки за свои монеты или TON:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("market_buy_"))
async def market_buy_callback(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    if item_id not in MARKET_ITEMS:
        return await callback.answer("❌ Товар не найден!", show_alert=True)
        
    item = MARKET_ITEMS[item_id]
    
    kb = [
        [
            InlineKeyboardButton(text=f"💰 {item['coins']:,} монет", callback_data=f"market_pay_coins_{item_id}"),
            InlineKeyboardButton(text=f"💎 {item['ton']} TON", callback_data=f"market_pay_ton_{item_id}")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_back")]
    ]
    
    await callback.message.edit_text(
        f"🛍 **Покупка NFT:**\n\n"
        f"🎁 Подарок: **{item['name']}**\n"
        f"Выберите способ оплаты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("market_pay_"))
async def market_pay_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    method = parts[2]
    item_id = parts[3]
    
    if item_id not in MARKET_ITEMS:
        return await callback.answer("❌ Товар не найден!", show_alert=True)
        
    item = MARKET_ITEMS[item_id]
    user = await db.get_user(callback.from_user.id)
    
    if method == "coins":
        if user[2] < item['coins']:
            return await callback.answer("❌ Недостаточно монет!", show_alert=True)
        await db.update_balance(callback.from_user.id, -item['coins'])
        cost_text = f"💰 {item['coins']:,} монет"
    else:
        if user[6] < item['ton']:
            return await callback.answer("❌ Недостаточно TON!", show_alert=True)
        await db.update_ton(callback.from_user.id, -item['ton'])
        cost_text = f"💎 {item['ton']} TON"
        
    await db.add_nft(callback.from_user.id, item['name'])
    
    await callback.message.edit_text(
        f"🎉 **Успешная покупка!**\n\n"
        f"🎁 Вы купили **{item['name']}** за {cost_text}!\n"
        f"Подарок добавлен в ваш инвентарь. Используйте `🎁 Мои подарки` чтобы посмотреть."
    )
    await callback.answer("✅ Куплено!")

@router.message(F.text == "🎁 Мои подарки")
async def my_gifts_cmd(message: Message):
    user_nfts = await db.get_user_nfts(message.from_user.id)
    if not user_nfts:
        await message.answer("🎁 **У вас пока нет подарков.**\nПолучите их от друзей или администрации!")
        return
        
    text = "🎁 **Ваши подарки:**\n\n"
    for nft in user_nfts:
        status = f"📌 Слот {nft[5]}" if nft[4] == 1 else "🗄 В инвентаре"
        text += f"• **{nft[2]}** (ID: `{nft[0]}`) — Ур. `{nft[3]}` ({status})\n"
    await message.answer(text)

@router.callback_query(F.data == "nft_my")
async def nft_my_callback(callback: CallbackQuery):
    user_nfts = await db.get_user_nfts(callback.from_user.id)
    if not user_nfts:
        return await callback.answer("🎁 У вас пока нет подарков!", show_alert=True)
        
    text = "🎁 **Ваши подарки:**\n\n"
    for nft in user_nfts:
        status = f"📌 Слот {nft[5]}" if nft[4] == 1 else "🗄 В инвентаре"
        text += f"• **{nft[2]}** (ID: `{nft[0]}`) — Ур. `{nft[3]}` ({status})\n"
        
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back")]
    ]))

@router.message(F.text == "📈 Мои активы")
async def my_assets_cmd(message: Message):
    user = await db.get_user(message.from_user.id)
    await message.answer(f"📈 **Ваши активы:**\n\n💰 Баланс: `{user[2]:,}` монет\n💎 TON: `{user[6]:.2f}` TON")

@router.message(TextStartsWith("📌 закрепить", "закрепить"))
async def equip_gift_cmd(message: Message):
    text = message.text
    if text.lower().startswith("📌 закрепить"):
        clean_text = text[11:].strip()
    else:
        clean_text = text[9:].strip()
        
    parts = clean_text.split()
    if len(parts) < 2:
        await message.answer("ℹ️ Пример команды:\n`📌 Закрепить [название] [ID] [слот (1-6)]`\n\n*Пример: 📌 Закрепить Звезда 5 1*")
        return
        
    try:
        slot = int(parts[-1])
        nft_id = int(parts[-2])
        name = " ".join(parts[:-2]).strip()
    except ValueError:
        await message.answer("❌ ID подарка и слот должны быть числами!")
        return
        
    if slot < 1 or slot > 6:
        await message.answer("❌ Слот должен быть от 1 до 6!")
        return
        
    nft = await db.get_nft(nft_id)
    if not nft or nft[1] != message.from_user.id:
        await message.answer("❌ У вас нет NFT с таким ID!")
        return
        
    if nft[2].lower() != name.lower():
        await message.answer(f"❌ Название подарка не совпадает! Настоящее название: **{nft[2]}**")
        return
        
    await db.equip_nft(nft_id, slot)
    await message.answer(f"✅ Подарок **{nft[2]}** (ID: `{nft_id}`) закреплен на слот `{slot}`!")

@router.message(TextStartsWith("🕶 надеть", "надеть"))
async def equip_auto_cmd(message: Message):
    text = message.text
    if text.lower().startswith("🕶 надеть"):
        clean_text = text[8:].strip()
    else:
        clean_text = text[6:].strip()
        
    parts = clean_text.split()
    if len(parts) < 2:
        await message.answer("ℹ️ Пример команды:\n`🕶 Надеть [название] [ID]`\n\n*Пример: 🕶 Надеть Звезда 5*")
        return
        
    try:
        nft_id = int(parts[-1])
        name = " ".join(parts[:-1]).strip()
    except ValueError:
        await message.answer("❌ ID подарка должен быть числом!")
        return
        
    nft = await db.get_nft(nft_id)
    if not nft or nft[1] != message.from_user.id:
        await message.answer("❌ У вас нет NFT с таким ID!")
        return
        
    if nft[2].lower() != name.lower():
        await message.answer(f"❌ Название подарка не совпадает! Настоящее название: **{nft[2]}**")
        return
        
    user_nfts = await db.get_user_nfts(message.from_user.id)
    equipped_slots = {n[5] for n in user_nfts if n[4] == 1}
    
    free_slot = None
    for slot in range(1, 7):
        if slot not in equipped_slots:
            free_slot = slot
            break
            
    if free_slot is None:
        await message.answer("❌ У вас заняты все 6 слотов! Сначала открепите что-то: `✂️ Открепить [слот]`.")
        return
        
    await db.equip_nft(nft_id, free_slot)
    await message.answer(f"✅ Подарок **{nft[2]}** (ID: `{nft_id}`) надет на слот `{free_slot}`!")

@router.message(TextStartsWith("✂️ открепить", "открепить"))
async def unequip_gift_cmd(message: Message):
    text = message.text
    if text.lower().startswith("✂️ открепить"):
        clean_text = text[12:].strip()
    else:
        clean_text = text[9:].strip()
        
    parts = clean_text.split()
    if not parts or not parts[0].isdigit():
        await message.answer("ℹ️ Пример команды:\n`✂️ Открепить [номер слота (1-6)]`\n\n*Пример: ✂️ Открепить 2*")
        return
        
    slot = int(parts[0])
    if slot < 1 or slot > 6:
        await message.answer("❌ Слот должен быть от 1 до 6!")
        return
        
    user_nfts = await db.get_user_nfts(message.from_user.id)
    equipped_nft = next((n for n in user_nfts if n[4] == 1 and n[5] == slot), None)
    
    if not equipped_nft:
        await message.answer(f"❌ Слот `{slot}` уже пуст!")
        return
        
    await db.unequip_nft(message.from_user.id, slot)
    await message.answer(f"✅ Подарок **{equipped_nft[2]}** откреплен из слота `{slot}`!")

@router.message(TextStartsWith("🔍 сподарок", "сподарок"))
async def inspect_gift_cmd(message: Message):
    text = message.text
    if text.lower().startswith("🔍 сподарок"):
        clean_text = text[11:].strip()
    else:
        clean_text = text[9:].strip()
        
    parts = clean_text.split()
    if len(parts) < 2:
        await message.answer("ℹ️ Пример команды:\n`🔍 Сподарок [название] [ID]`\n\n*Пример: 🔍 Сподарок Звезда 5*")
        return
        
    try:
        nft_id = int(parts[-1])
        name = " ".join(parts[:-1]).strip()
    except ValueError:
        await message.answer("❌ ID подарка должен быть числом!")
        return
        
    nft = await db.get_nft(nft_id)
    if not nft:
        await message.answer("❌ Подарок не найден!")
        return
        
    owner = await db.get_user(nft[1])
    owner_name = f"@{owner[1]}" if owner and owner[1] else f"ID {nft[1]}"
    status = f"📌 Закреплен (слот {nft[5]})" if nft[4] == 1 else "🗄 В инвентаре"
    
    text_info = (
        f"🔍 **Информация об NFT:**\n\n"
        f"🆔 ID: `{nft[0]}`\n"
        f"🎁 Название: **{nft[2]}**\n"
        f"⭐️ Уровень: `{nft[3]}`\n"
        f"👤 Владелец: {owner_name}\n"
        f"📊 Статус: {status}"
    )
    await message.answer(text_info)

@router.message(TextStartsWith("✨ стоимость улучшения"))
async def upgrade_costs_cmd(message: Message):
    text = (
        "✨ **Стоимость улучшения NFT подарков:**\n\n"
        "⭐️ `Ур. 1 -> 2`: 💰 `15,000` монет или 💎 `0.10` TON\n"
        "⭐️ `Ур. 2 -> 3`: 💰 `30,000` монет или 💎 `0.20` TON\n"
        "⭐️ `Ур. 3 -> 4`: 💰 `60,000` монет или 💎 `0.40` TON\n"
        "⭐️ `Ур. 4 -> 5`: 💰 `120,000` монет или 💎 `0.80` TON\n"
        "⭐️ `Ур. 5 -> 6`: 💰 `240,000` монет или 💎 `1.60` TON\n"
        "⭐️ `Ур. 6 -> 7`: 💰 `480,000` монет или 💎 `3.20` TON\n"
        "⭐️ `Ур. 7 -> 8`: 💰 `960,000` монет или 💎 `6.40` TON\n"
        "⭐️ `Ур. 8 -> 9`: 💰 `1,920,000` монет или 💎 `12.80` TON\n"
        "⭐️ `Ур. 9 -> 10`: 💰 `3,840,000` монет или 💎 `25.60` TON\n\n"
        "ℹ️ Для улучшения используйте команду:\n`🆙 Подарок улучшить [название]`"
    )
    await message.answer(text)

@router.message(TextStartsWith("🆙 подарок улучшить", "подарок улучшить"))
async def upgrade_gift_cmd(message: Message):
    text = message.text
    if text.lower().startswith("🆙 подарок улучшить"):
        name = text[18:].strip()
    else:
        name = text[16:].strip()
        
    if not name:
        await message.answer("ℹ️ Укажите название подарка!\nПример: `🆙 Подарок улучшить Звезда`")
        return
        
    user_nfts = await db.get_user_nfts(message.from_user.id)
    target_nfts = [n for n in user_nfts if n[2].lower() == name.lower()]
    if not target_nfts:
        await message.answer(f"❌ У вас нет подарка с названием '{name}'!")
        return
        
    nft_to_upgrade = next((n for n in sorted(target_nfts, key=lambda x: x[3]) if x[3] < 10), None)
    if not nft_to_upgrade:
        await message.answer(f"❌ Все ваши подарки с названием '{name}' уже максимального уровня (10)!")
        return
        
    nft_id = nft_to_upgrade[0]
    current_level = nft_to_upgrade[3]
    next_level = current_level + 1
    
    coins_cost = 15000 * (2 ** (current_level - 1))
    ton_cost = 0.1 * (2 ** (current_level - 1))
    
    kb = [
        [
            InlineKeyboardButton(text=f"💰 {coins_cost:,} монет", callback_data=f"upg_coins_{nft_id}"),
            InlineKeyboardButton(text=f"💎 {ton_cost:.2f} TON", callback_data=f"upg_ton_{nft_id}")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_back")]
    ]
    
    await message.answer(
        f"🆙 **Улучшение подарка:**\n\n"
        f"🎁 Подарок: **{nft_to_upgrade[2]}** (ID: `{nft_id}`)\n"
        f"⭐️ Уровень: `{current_level}` ➡️ `{next_level}`\n\n"
        f"Выберите способ оплаты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("upg_"))
async def upgrade_confirm_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    method = parts[1]
    nft_id = int(parts[2])
    
    nft = await db.get_nft(nft_id)
    if not nft or nft[1] != callback.from_user.id:
        return await callback.answer("❌ Вы не владелец этого подарка!", show_alert=True)
        
    current_level = nft[3]
    if current_level >= 10:
        return await callback.answer("❌ Подарок уже максимального уровня!", show_alert=True)
        
    coins_cost = 15000 * (2 ** (current_level - 1))
    ton_cost = 0.1 * (2 ** (current_level - 1))
    
    user = await db.get_user(callback.from_user.id)
    if method == "coins":
        if user[2] < coins_cost:
            return await callback.answer("❌ Недостаточно монет!", show_alert=True)
        await db.update_balance(callback.from_user.id, -coins_cost)
    else:
        if user[6] < ton_cost:
            return await callback.answer("❌ Недостаточно TON!", show_alert=True)
        await db.update_ton(callback.from_user.id, -ton_cost)
        
    new_level = current_level + 1
    await db.update_nft_level(nft_id, new_level)
    
    await callback.message.edit_text(
        f"🎉 **Успешное улучшение!**\n\n"
        f"🎁 Подарок **{nft[2]}** (ID: `{nft_id}`) улучшен до уровня `{new_level}`!\n"
        f"💸 Списано: " + (f"`{coins_cost:,}` монет" if method == "coins" else f"`{ton_cost:.2f}` TON")
    )
    await callback.answer("✅ Улучшено!")

@router.message(TextStartsWith("🗄 передать", "передать"))
async def transfer_gift_cmd(message: Message):
    text = message.text
    if text.lower().startswith("🗄 передать"):
        clean_text = text[10:].strip()
    else:
        clean_text = text[8:].strip()
        
    parts = clean_text.split()
    if len(parts) < 3:
        await message.answer("ℹ️ Пример команды:\n`🗄 Передать [ID/юзернейм] [название] [ID подарка]`\n\n*Пример: 🗄 Передать @user Звезда 5*")
        return
        
    user_identifier = parts[0]
    try:
        nft_id = int(parts[-1])
        name = " ".join(parts[1:-1]).strip()
    except ValueError:
        await message.answer("❌ ID подарка должен быть числом!")
        return
        
    nft = await db.get_nft(nft_id)
    if not nft or nft[1] != message.from_user.id:
        await message.answer("❌ У вас нет NFT с таким ID!")
        return
        
    if nft[2].lower() != name.lower():
        await message.answer(f"❌ Название не совпадает! Настоящее название: **{nft[2]}**")
        return
        
    target_user = await db.resolve_user(user_identifier)
    if not target_user:
        await message.answer("❌ Получатель не найден!")
        return
        
    target_user_id = target_user[0]
    if target_user_id == message.from_user.id:
        await message.answer("❌ Нельзя передать подарок самому себе!")
        return
        
    await db.update_nft_owner(nft_id, target_user_id)
    await message.answer(f"✅ Успешно передано **{nft[2]}** (ID: `{nft_id}`) игроку {user_identifier}!")
    
    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=f"🎁 Игрок @{message.from_user.username or message.from_user.id} передал вам подарок **{nft[2]}** (ID: `{nft_id}`)!"
        )
    except Exception:
        pass

@router.message(F.text.startswith("🤝 Сделка"))
async def deal_gift_cmd(message: Message):
    await message.answer("❌ Для создания сделки нужно иметь NFT подарок.")

@router.message(F.text == "📄 Сделки")
async def deals_list_cmd(message: Message):
    await message.answer("📄 **Список активных сделок пуст.**")
