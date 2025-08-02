import asyncio
import json
import os
import random
from datetime import date

# Для загрузки токена из .env файла
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)

# ------------------ НАСТРОЙКИ ------------------
load_dotenv() # Загружаем переменные из .env файла

BOT_TOKEN = os.getenv("BOT_TOKEN") or "ВСТАВЬ_СЮДА_ТОКEN"
# Используем set для быстрой проверки и удаления кодов
PRO_CODES = {"PRO2025", "BESTUSER"}
VTB_CARD = "2200 1111 2222 3333"
ADMIN_ID = 123456789 # Укажите свой Telegram ID для уведомлений

# ------------------ ИНИЦИАЛИЗАЦИЯ ------------------
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ------------------ ХРАНИЛИЩЕ ДАННЫХ (JSON) ------------------
USERS_FILE = "users_data.json"

def load_users_data():
    """Загружает данные пользователей из JSON-файла."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users_data(data):
    """Сохраняет данные пользователей в JSON-файл."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ------------------ СОСТОЯНИЯ (FSM) ------------------
class UserAction(StatesGroup):
    waiting_for_income = State()
    waiting_for_expense = State()
    waiting_for_goal = State()
    waiting_for_pro_code = State()

# ------------------ КЛАВИАТУРЫ ------------------
def get_main_reply_keyboard():
    """Возвращает главную клавиатуру с кнопкой 'Меню'."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="☰ Меню")]],
        resize_keyboard=True,
        input_field_placeholder="Нажмите 'Меню', чтобы начать..."
    )

def get_main_inline_keyboard(user_id: str):
    """Возвращает главное инлайн-меню с иконками."""
    users_data = load_users_data()
    is_pro = users_data.get(user_id, {}).get("pro", False)
    pro_icon = "⭐" if is_pro else "🔓"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Доход", callback_data="add_income"),
            InlineKeyboardButton(text="➖ Расход", callback_data="add_expense")
        ],
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="goals_menu")],
        [InlineKeyboardButton(text="💡 Совет дня", callback_data="tips")],
        [InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="donate")],
        [InlineKeyboardButton(text=f"{pro_icon} PRO-доступ", callback_data="pro_menu")]
    ])

def get_back_button(callback_data="main_menu"):
    """Возвращает кнопку 'Назад'."""
    return InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)

# ------------------ ГЛАВНОЕ МЕНЮ И СТАРТ ------------------
async def show_main_menu(message: Message, text: str):
    """Отправляет или редактирует сообщение, показывая главное инлайн-меню."""
    uid = str(message.from_user.id)
    users_data = load_users_data()
    balance = users_data.get(uid, {}).get("balance", 0)
    
    full_text = f"{text}\n\n<b>Текущий баланс:</b> {balance:,.2f} ₽"
    
    # Используем edit_text если возможно, иначе answer
    try:
        await message.edit_text(full_text, reply_markup=get_main_inline_keyboard(uid))
    except Exception:
        await message.answer(full_text, reply_markup=get_main_inline_keyboard(uid))

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear() # Сбрасываем состояние при старте
    uid = str(message.from_user.id)
    users_data = load_users_data()
    if uid not in users_data:
        users_data[uid] = {
            "balance": 0.0,
            "history": [],
            "goals": {},
            "pro": False
        }
        save_users_data(users_data)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}! Я твой финансовый помощник.",
        reply_markup=get_main_reply_keyboard()
    )
    await show_main_menu(message, "Выбери действие:")

# Новый обработчик для кнопки '☰ Меню'
@dp.message(F.text == "☰ Меню")
async def handle_menu_button(message: Message):
    await show_main_menu(message, "Главное меню:")

@dp.callback_query(F.data == "main_menu")
async def cq_main_menu(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer()
    await show_main_menu(cq.message, "Главное меню:")

# ------------------ ДОХОДЫ И РАСХОДЫ ------------------
@dp.callback_query(F.data.in_({"add_income", "add_expense"}))
async def cq_add_transaction(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    if cq.data == "add_income":
        await state.set_state(UserAction.waiting_for_income)
        await cq.message.edit_text(
            "Введите сумму дохода и описание:\n<i>Пример: 50000 Зарплата</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]])
        )
    else:
        await state.set_state(UserAction.waiting_for_expense)
        await cq.message.edit_text(
            "Введите сумму расхода и описание:\n<i>Пример: 250 Кофе</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]])
        )

@dp.message(F.text, UserAction.waiting_for_income)
@dp.message(F.text, UserAction.waiting_for_expense)
async def process_transaction(message: Message, state: FSMContext):
    current_state = await state.get_state()
    op_type = "income" if current_state == UserAction.waiting_for_income else "expense"
    
    try:
        parts = message.text.split(maxsplit=1)
        amount = abs(float(parts[0].replace(',', '.')))
        desc = parts[1] if len(parts) > 1 else "Без описания"
    except (ValueError, IndexError):
        await message.answer("❌ <b>Ошибка!</b> Неверный формат.\nПопробуйте ещё раз, например: <b>1000 Продукты</b>")
        return

    await state.clear()
    uid = str(message.from_user.id)
    users_data = load_users_data()

    if op_type == "income":
        users_data[uid]["balance"] += amount
    else:
        users_data[uid]["balance"] -= amount
    
    users_data[uid]["history"].append({
        "date": date.today().isoformat(), "type": op_type, "amount": amount, "desc": desc
    })
    save_users_data(users_data)
    
    await show_main_menu(message, f"✅ Запись добавлена: <b>{desc} ({amount:,.2f} ₽)</b>")

# ------------------ ЦЕЛИ ------------------
def get_progress_bar(current, target):
    """Создает текстовый прогресс-бар."""
    progress = (current / target) * 100 if target > 0 else 100
    progress = min(progress, 100)
    filled_blocks = int(progress / 10)
    empty_blocks = 10 - filled_blocks
    return f"[{'█' * filled_blocks}{'░' * empty_blocks}] {progress:.1f}%"

@dp.callback_query(F.data == "goals_menu")
async def cq_goals_menu(cq: CallbackQuery):
    await cq.answer()
    uid = str(cq.from_user.id)
    users_data = load_users_data()
    user_goals = users_data.get(uid, {}).get("goals", {})
    balance = users_data.get(uid, {}).get("balance", 0)
    
    text = "🎯 <b>Ваши финансовые цели:</b>\n\n"
    kb_list = [[InlineKeyboardButton(text="➕ Добавить новую цель", callback_data="add_goal")]]
    
    if not user_goals:
        text += "У вас пока нет целей. Самое время это исправить!"
    else:
        for name, target in user_goals.items():
            # Для простоты считаем прогресс от общего баланса
            text += f"<b>{name}</b> ({balance:,.2f} / {target:,.2f} ₽)\n{get_progress_bar(balance, target)}\n\n"
            kb_list.append([InlineKeyboardButton(text=f"❌ Удалить '{name}'", callback_data=f"del_goal:{name}")])

    kb_list.append([get_back_button()])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))

@dp.callback_query(F.data == "add_goal")
async def cq_add_goal(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(UserAction.waiting_for_goal)
    await cq.message.edit_text(
        "Введите название цели и её стоимость через пробел.\n<i>Пример: Новый телефон 30000</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("goals_menu")]])
    )

@dp.message(F.text, UserAction.waiting_for_goal)
async def process_new_goal(message: Message, state: FSMContext):
    try:
        # rsplit позволяет именам целей содержать пробелы
        name, target_str = message.text.rsplit(maxsplit=1)
        target = float(target_str.replace(',', '.'))
        if target <= 0: raise ValueError
    except (ValueError, IndexError):
        await message.answer("❌ <b>Ошибка!</b> Неверный формат.\nВведите, например: <b>Отпуск на море 150000</b>")
        return

    await state.clear()
    uid = str(message.from_user.id)
    users_data = load_users_data()
    users_data[uid]["goals"][name.strip()] = target
    save_users_data(users_data)
    
    await message.answer(f"✅ Цель «{name.strip()}» на {target:,.2f} ₽ создана!")
    # Имитируем CallbackQuery для вызова меню целей
    await cq_goals_menu(CallbackQuery(id="dummy", from_user=message.from_user, message=message, chat_instance="dummy"))
    
@dp.callback_query(F.data.startswith("del_goal:"))
async def cq_delete_goal(cq: CallbackQuery):
    goal_to_delete = cq.data.split(":", 1)[1]
    uid = str(cq.from_user.id)
    users_data = load_users_data()
    
    if goal_to_delete in users_data[uid]["goals"]:
        del users_data[uid]["goals"][goal_to_delete]
        save_users_data(users_data)
        await cq.answer(f"✅ Цель '{goal_to_delete}' удалена!")
    else:
        await cq.answer("Цель не найдена.", show_alert=True)
    await cq_goals_menu(cq)

# ------------------ СОВЕТЫ ------------------
TIPS = [
    "Ведите учёт каждый день, это занимает не более 5 минут.",
    "Определите 3 приоритетные финансовые цели на год.",
    "Используйте правило 50/30/20: 50% на нужды, 30% на желания, 20% на сбережения.",
    "Создайте 'подушку безопасности' — запас денег на 3-6 месяцев жизни без дохода.",
    "Избегайте импульсивных покупок. Перед тем как что-то купить, подождите 24 часа."
]

@dp.callback_query(F.data == "tips")
async def cq_tips(cq: CallbackQuery):
    await cq.answer()
    tip = random.choice(TIPS)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другой совет", callback_data="tips")],
        [get_back_button()]
    ])
    await cq.message.edit_text(f"<b>💡 Финансовый совет:</b>\n\n<i>{tip}</i>", reply_markup=kb)

# ------------------ ПОДДЕРЖКА ПРОЕКТА ------------------
@dp.callback_query(F.data == "donate")
async def cq_donate(cq: CallbackQuery):
    await cq.answer()
    text = (
        "Спасибо за ваш интерес к поддержке проекта! ❤️\n\n"
        "Ваш вклад поможет боту развиваться.\n\n"
        "Перевести любую сумму можно по номеру карты (ВТБ):\n"
        f"<code>{VTB_CARD}</code> 👈 (нажмите, чтобы скопировать)"
    )
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]]))

# ------------------ PRO-ДОСТУП ------------------
@dp.callback_query(F.data == "pro_menu")
async def cq_pro_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    uid = str(cq.from_user.id)
    users_data = load_users_data()
    if users_data.get(uid, {}).get("pro", False):
        await cq.message.edit_text(
            "⭐ У вас уже есть PRO-доступ! Спасибо за поддержку!\n\n"
            "<i>В будущих версиях здесь появятся PRO-функции (например, экспорт данных).</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]])
        )
    else:
        await state.set_state(UserAction.waiting_for_pro_code)
        await cq.message.edit_text(
            "Введите ваш PRO-код для активации:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]])
        )

@dp.message(F.text, UserAction.waiting_for_pro_code)
async def process_pro_code(message: Message, state: FSMContext):
    await state.clear()
    code = message.text.strip().upper()
    if code in PRO_CODES:
        uid = str(message.from_user.id)
        users_data = load_users_data()
        users_data[uid]["pro"] = True
        save_users_data(users_data)
        
        # Код одноразовый, удаляем его.
        # Внимание: при перезапуске бота список кодов восстановится.
        # Для постоянства нужно хранить использованные коды в файле или БД.
        PRO_CODES.remove(code)
        
        await message.answer("✅ <b>Поздравляем!</b> PRO-доступ успешно активирован!")
        await show_main_menu(message, "Теперь вам доступны все возможности.")
    else:
        await message.answer("❌ Неверный или уже использованный код.")
        await show_main_menu(message, "Попробуйте снова или вернитесь в меню.")

# ------------------ ОБРАБОТКА НЕИЗВЕСТНЫХ КОМАНД ------------------
@dp.message()
async def handle_unknown_message(message: Message, state: FSMContext):
    # Сбрасываем состояние, если пользователь что-то пишет не по сценарию
    await state.clear()
    await message.answer(
        "Неизвестная команда. Нажмите на кнопку <b>☰ Меню</b>, чтобы увидеть все доступные действия.",
        reply_markup=get_main_reply_keyboard()
    )

# ------------------ ЗАПУСК БОТА ------------------
async def main():
    # Создаем файл данных, если его нет
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
            
    print("Бот запущен...")
    # Удаляем вебхук, если он был установлен ранее
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
