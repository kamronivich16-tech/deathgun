import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import db
import config

router = Router()

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
    text = (
        f"👤 **Профиль:**\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"💰 Баланс: `{user[2]:,}` монет\n\n"
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
        [InlineKeyboardButton(text="➕ Выдать", callback_data="adm_give"), InlineKeyboardButton(text="➖ Забрать", callback_data="adm_take")],
        [InlineKeyboardButton(text="🔨 Бан", callback_data="adm_ban"), InlineKeyboardButton(text="🕊 Разбан", callback_data="adm_unban")],
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
        return

    await state.update_data(admin_act=act)
    await state.set_state(AdminStates.waiting_for_id_give if act == "give" else AdminStates.waiting_for_id_take if act == "take" else AdminStates.waiting_for_id_ban if act == "ban" else AdminStates.waiting_for_id_unban)
    await callback.message.answer("✍️ **Введите ID пользователя:**")

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

@router.message(F.text == "🛍 Маркет")
async def market_cmd(message: Message):
    await message.answer("🛍 **Маркет временного не доступен.**\nСкоро здесь появятся лучшие предложения!")

@router.message(F.text == "🎁 Мои подарки")
async def my_gifts_cmd(message: Message):
    await message.answer("🎁 **У вас пока нет подарков.**\nКупите их в маркете или получите от друзей!")

@router.message(F.text == "📈 Мои активы")
async def my_assets_cmd(message: Message):
    user = await db.get_user(message.from_user.id)
    await message.answer(f"📈 **Ваши активы:**\n\n💰 Баланс: `{user[2]:,}` монет\n💎 TON: `0.00` (в разработке)")

@router.message(F.text.startswith("🆙 Подарок улучшить"))
async def upgrade_gift_cmd(message: Message):
    await message.answer("❌ У вас нет этого подарка для улучшения!")

@router.message(F.text.startswith("🗄 Передать"))
async def transfer_gift_cmd(message: Message):
    await message.answer("❌ Ошибка передачи. Проверьте ID подарка или пользователя.")

@router.message(F.text.startswith("🤝 Сделка"))
async def deal_gift_cmd(message: Message):
    await message.answer("❌ Для создания сделки нужно иметь NFT подарок.")

@router.message(F.text == "📄 Сделки")
async def deals_list_cmd(message: Message):
    await message.answer("📄 **Список активных сделок пуст.**")
