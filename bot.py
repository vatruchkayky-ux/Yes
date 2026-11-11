import asyncio
import time
import random
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9007446269:AAHS11dx4OuNjYLZt6bTp9vwhb1Jufo2_Qw"
ADMIN_ID = 7510323045
DB_FILE = "users.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
TZ = ZoneInfo("Asia/Yekaterinburg") 

# --- РАБОТА С БАЗОЙ ДАННЫХ (JSON) ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def draw_bar(value):
    if value >= 70: color = "🟩"
    elif value >= 40: color = "🟨"
    else: color = "🟥"
    filled = int(value // 10)
    empty = 10 - filled
    return f"{color * filled}{'⬜' * empty} {value}%"

class CreatePet(StatesGroup):
    name = State()
    photo = State()
    char = State()

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="🍔 Покормить"), KeyboardButton(text="💧 Попить")],
        [KeyboardButton(text="🛌 Поспать"), KeyboardButton(text="🎾 Поиграть")],
        [KeyboardButton(text="📊 Профиль"), KeyboardButton(text="💬 Поговорить")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🎒 Инвентарь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

SHOP_ITEMS = {
    "apple": {"name": "🍎 Яблоко", "price": 20, "effect": "hunger", "value": 15},
    "burger": {"name": "🍔 Бургер", "price": 60, "effect": "hunger", "value": 40},
    "water": {"name": "🥛 Вода", "price": 10, "effect": "thirst", "value": 20},
    "juice": {"name": "🧃 Сок", "price": 30, "effect": "thirst", "value": 40},
    "pill": {"name": "💊 Таблетка", "price": 150, "effect": "heal", "value": 1},
    "soap": {"name": "🧼 Мыло", "price": 50, "effect": "wash", "value": 1},
    "ball": {"name": "⚽ Мячик", "price": 80, "effect": "mood", "value": 30},
    "toy": {"name": "🧸 Игрушка", "price": 150, "effect": "mood", "value": 60}
}

# --- ФОНОВАЯ ЗАДАЧА (Сон и уведомления) ---
async def background_worker():
    while True:
        try:
            now = datetime.now(TZ)
            if now.hour >= 23 or now.hour < 8:
                await asyncio.sleep(1800)
                continue

            users = load_db()
            current_time = int(time.time())
            
            for uid_str, user in users.items():
                if user.get('is_dead'): continue
                elapsed_mins = (current_time - user['last_update']) / 60
                drop = int(elapsed_mins / 5)
                
                if drop > 0:
                    user['hunger'] = max(0, user['hunger'] - drop)
                    user['thirst'] = max(0, user['thirst'] - drop)
                    user['energy'] = max(0, user['energy'] - drop)
                    user['mood'] = max(0, user['mood'] - drop)
                    user['last_update'] = current_time
                    
                    if user['hunger'] == 0 or user['thirst'] == 0: user['is_dead'] = True
                        
                    if user['hunger'] < 30 or user['thirst'] < 30:
                        try: await bot.send_message(int(uid_str), f"⚠️ {user['pet_name']} голоден!\n🍔 {user['hunger']}% | 💧 {user['thirst']}%")
                        except: pass
            save_db(users)
        except Exception as e:
            print(f"Ошибка фона: {e}")
        await asyncio.sleep(900)

# --- СТАРТ ---
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    users = load_db()
    uid = str(message.from_user.id)
    
    if uid in users:
        users[uid]['username'] = message.from_user.username or "Нет юзернейма"
        save_db(users)
        await message.answer(f"С возвращением! {users[uid]['pet_name']} скучал.\n🪙 Монеты: {users[uid]['coins']}", reply_markup=get_main_keyboard())
        return

    await message.answer("⚠️ Внимание! Каким ты создашь персонажа сейчас, таким он останется навсегда!")
    await message.answer("Шаг 1. Введи имя для твоего персонажа:")
    await state.set_state(CreatePet.name)

# --- ДЕЙСТВИЯ ---
@dp.message(F.text == "🍔 Покормить")
async def feed_pet(message: Message):
    users = load_db()
    uid = str(message.from_user.id)
    if uid not in users: return
    users[uid]['hunger'] = min(100, users[uid]['hunger'] + 20)
    users[uid]['last_update'] = int(time.time())
    save_db(users)
    await message.answer(f"🍔 Ты покормил {users[uid]['pet_name']}!\nСытость: {draw_bar(users[uid]['hunger'])}\n🪙 Монеты: {users[uid]['coins']}")

@dp.message(F.text == "💧 Попить")
async def water_pet(message: Message):
    users = load_db()
    uid = str(message.from_user.id)
    if uid not in users: return
    users[uid]['thirst'] = min(100, users[uid]['thirst'] + 20)
    users[uid]['last_update'] = int(time.time())
    save_db(users)
    await message.answer(f"💧 {users[uid]['pet_name']} попил!\nЖажда: {draw_bar(users[uid]['thirst'])}\n🪙 Монеты: {users[uid]['coins']}")

@dp.message(F.text == "🎾 Поиграть")
async def play_pet(message: Message):
    users = load_db()
    uid = str(message.from_user.id)
    if uid not in users: return
    users[uid]['mood'] = min(100, users[uid]['mood'] + 20)
    users[uid]['last_update'] = int(time.time())
    save_db(users)
    await message.answer(f"🎾 Ты поиграл!\nНастроение: {draw_bar(users[uid]['mood'])}\n🪙 Монеты: {users[uid]['coins']}")

@dp.message(F.text == "💬 Поговорить")
async def talk_to_pet(message: Message):
    users = load_db()
    uid = str(message.from_user.id)
    if uid not in users: return
    phrases = ["Привет! 🤍", "Я тебя люблю!", "Давай играть!", "Я голоден..."]
    await message.answer(f"💬 {users[uid]['pet_name']}: «{random.choice(phrases)}»")

@dp.message(F.text == "📊 Профиль")
async def show_profile(message: Message):
    users = load_db()
    uid = str(message.from_user.id)
    if uid not in users: return
    u = users[uid]
    text = f"📊 **Профиль**\n\n👤 **Имя:** {u['pet_name']}\n🪙 **Монеты:** {u['coins']}\n\n🍔 Сытость: {draw_bar(u['hunger'])}\n💧 Жажда: {draw_bar(u['thirst'])}\n🎾 Настроение: {draw_bar(u['mood'])}"
    await message.answer_photo(photo=u['pet_photo'], caption=text, parse_mode="Markdown")

# --- МАГАЗИН ---
@dp.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍎 Яблоко (20🪙)", callback_data="buy_apple")],
        [InlineKeyboardButton(text="🥛 Вода (10🪙)", callback_data="buy_water")],
        [InlineKeyboardButton(text="⚽ Мячик (80🪙)", callback_data="buy_ball")]
    ])
    await message.answer("🛒 **Магазин**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(call: CallbackQuery):
    users = load_db()
    uid = str(call.from_user.id)
    if uid not in users: return
    item = call.data.replace("buy_", "")
    price = SHOP_ITEMS[item]["price"]
    if users[uid]['coins'] < price: return await call.answer("Мало монет!", show_alert=True)
    
    users[uid]['coins'] -= price
    if item == "apple": users[uid]['hunger'] = min(100, users[uid]['hunger'] + 15)
    elif item == "water": users[uid]['thirst'] = min(100, users[uid]['thirst'] + 20)
    elif item == "ball": users[uid]['mood'] = min(100, users[uid]['mood'] + 30)
    
    save_db(users)
    await call.message.answer(f"✅ Куплено! Остаток: {users[uid]['coins']} 🪙")
    await call.answer()

# --- АДМИН ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID: return
    users = load_db()
    if not users: return await message.answer("Игроков нет.")
    
    kb_buttons = []
    for uid, data in users.items():
        uname = data.get('username', 'Нет юзернейма')
        name = data.get('pet_name', '???')
        coins = data.get('coins', 0)
        kb_buttons.append([InlineKeyboardButton(text=f"{name} (@{uname}) | 🪙 {coins}", callback_data=f"admin_user_{uid}")])
    await message.answer("👑 **Админ-панель**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("admin_user_"))
async def admin_user_actions(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    target = call.data.replace("admin_user_", "")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+ 100 🪙", callback_data=f"give_{target}_100")],
        [InlineKeyboardButton(text="+ 500 🪙", callback_data=f"give_{target}_500")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    await call.message.edit_text(f"Выбери сумму для {target}:", reply_markup=kb)

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    await admin_panel(call.message)

@dp.callback_query(F.data.startswith("give_"))
async def admin_give_coins(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    target, amount = parts[1], int(parts[2])
    users = load_db()
    if target in users:
        users[target]['coins'] += amount
        save_db(users)
        await call.answer(f"✅ Выдано {amount} монет!")
        try: await bot.send_message(int(target), f"🎁 Вам переслано {amount} 🪙!")
        except: pass
    await admin_panel(call.message)

# --- СОЗДАНИЕ ПЕРСОНАЖА ---
@dp.message(CreatePet.name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text) > 15: return await message.answer("Максимум 15 символов.")
    await state.update_data(name=message.text)
    await message.answer("Шаг 2. Отправь фото персонажа:")
    await state.set_state(CreatePet.photo)

@dp.message(CreatePet.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥰 Милый", callback_data="char_cute")], 
        [InlineKeyboardButton(text="😈 Вредный", callback_data="char_rude")],
        [InlineKeyboardButton(text="🧠 Умный", callback_data="char_smart")], 
        [InlineKeyboardButton(text="🤪 Безумный", callback_data="char_crazy")]
    ])
    await message.answer("Шаг 3. Выбери характер:", reply_markup=kb)
    await state.set_state(CreatePet.char)

@dp.callback_query(CreatePet.char, F.data.startswith("char_"))
async def process_char(call: CallbackQuery, state: FSMContext):
    char = call.data.replace("char_", "")
    data = await state.get_data()
    users = load_db()
    users[str(call.from_user.id)] = {
        "username": call.from_user.username or "Нет юзернейма",
        "pet_name": data['name'], "pet_photo": data['photo'], "pet_char": char,
        "age": 0, "hunger": 100, "thirst": 100, "energy": 100, "mood": 100,
        "coins": 100, "is_sick": False, "is_dirty": False, "is_dead": False, "last_update": int(time.time())
    }
    save_db(users)
    await state.clear()
    await call.message.answer("🎉 Персонаж создан!", reply_markup=get_main_keyboard())

async def main():
    asyncio.create_task(background_worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
