import asyncio
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем нашу базу
import database as db

BOT_TOKEN = "9007446269:AAHS11dx4OuNjYLZt6bTp9vwhb1Jufo2_Qw"
ADMIN_ID = 7510323045

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для создания
class CreatePet(StatesGroup):
    name = State()
    photo = State()
    char = State()

# Кнопки главного меню
def get_main_keyboard():
    kb = [
        [KeyboardButton(text="🍔 Покормить"), KeyboardButton(text="💧 Попить")],
        [KeyboardButton(text="🛌 Поспать"), KeyboardButton(text="🎾 Поиграть")],
        [KeyboardButton(text="📊 Профиль"), KeyboardButton(text="💬 Поговорить")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🎒 Инвентарь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Старт
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    
    if user:
        if user['is_dead']:
            # Логика воскрешения (в разработке)
            await message.answer(f"💀 {user['pet_name']} покинул этот мир.\nВоскресить его можно за 5000 🪙.", reply_markup=get_main_keyboard())
            return
        await message.answer(f"С возвращением! {user['pet_name']} скучал по тебе 🥰", reply_markup=get_main_keyboard())
        return

    # Если нет — начинаем создание
    await message.answer("⚠️ Внимание! Ты создаешь своего персонажа.\n\nКаким ты его назовешь, какое выберешь фото и характер — **навсегда**. Изменить это будет невозможно!")
    await message.answer("Шаг 1. Введи имя для своего персонажа:")
    await state.set_state(CreatePet.name)

@dp.message(CreatePet.name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text) > 15:
        await message.answer("Имя слишком длинное (максимум 15 символов). Попробуй еще раз:")
        return
    await state.update_data(name=message.text)
    await message.answer("Шаг 2. Отправь фото, как должен выглядеть твой персонаж (как обычную картинку):")
    await state.set_state(CreatePet.photo)

@dp.message(CreatePet.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    
    # Кнопки характера
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥰 Милый и ласковый", callback_data="char_cute")],
        [InlineKeyboardButton(text="😈 Вредный и дерзкий", callback_data="char_rude")],
        [InlineKeyboardButton(text="🧠 Умный и занудный", callback_data="char_smart")],
        [InlineKeyboardButton(text="🤪 Безумный и смешной", callback_data="char_crazy")]
    ])
    await message.answer("Шаг 3. Выбери характер персонажа (это тоже навсегда):", reply_markup=kb)
    await state.set_state(CreatePet.char)

@dp.callback_query(CreatePet.char, F.data.startswith("char_"))
async def process_char(call: CallbackQuery, state: FSMContext):
    char = call.data.replace("char_", "")
    data = await state.get_data()
    
    await db.create_user(call.from_user.id, data['name'], data['photo'], char)
    await state.clear()
    
    await call.message.answer("🎉 Персонаж успешно создан! Теперь твоя задача — заботиться о нем. Если не кормить и не поить, он может заболеть и даже умереть!", reply_markup=get_main_keyboard())
    await call.message.answer_photo(photo=data['photo'], caption=f"Знакомься, это {data['name']}!")

# Просмотр профиля (с полосками)
@dp.message(F.text == "📊 Профиль")
async def show_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала создай персонажа через /start")
        return
        
    text = (
        f"📊 **Профиль персонажа**\n\n"
        f"👤 Имя: {user['pet_name']}\n"
        f"🎭 Характер: {user['pet_char']}\n"
        f"🎂 Возраст: {user['age']} лет\n"
        f"🪙 Монеты: {user['coins']}\n\n"
        f"🍔 Сытость: {user['hunger']}%\n"
        f"💧 Жажда: {user['thirst']}%\n"
        f"⚡ Энергия: {user['energy']}%\n"
        f"🎾 Настроение: {user['mood']}%\n"
    )
    if user['is_dead']: text = "💀 **Персонаж мертв.**\n" + text
    elif user['is_sick']: text += "\n🦠 **Статус: Болен!**"
    elif user['is_dirty']: text += "\n💩 **Статус: Испачкался!**"

    await message.answer_photo(photo=user['pet_photo'], caption=text, parse_mode="Markdown")

# --- АДМИН ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return # Скрыто от всех
    
    await message.answer(
        "👑 **Админ-панель**\n\n"
        "Чтобы выдать монеты человеку, напиши:\n"
        "`/give ID СУММА`\n"
        "Например: `/give 12345678 1000`", 
        parse_mode="Markdown"
    )

@dp.message(Command("give"))
async def give_coins(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        target_id = int(args[1])
        amount = int(args[2])
        await db.add_coins(target_id, amount)
        await message.answer(f"✅ Выдано {amount} 🪙 пользователю {target_id}")
        # Уведомляем получателя
        try:
            await bot.send_message(target_id, f"🎁 Твой персонаж получил подарок от создателя: {amount} 🪙!")
        except:
            pass
    except:
        await message.answer("Ошибка. Формат: /give ID СУММА")

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())