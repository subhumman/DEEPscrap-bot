from aiogram import Bot, Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
import logging

import keyboards as kb
from database import get_all_categories, get_category_details
from config import config

logger = logging.getLogger(__name__)

router = Router()

# ---------------- FSM States -----------------
class CalculationStates(StatesGroup):
    waiting_for_meters = State()
    waiting_for_date = State()

# ---------------- Handlers -------------------

# /start command
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "<b>Добро пожаловать в бот по продаже металла!</b>\n\n"
        "Мы – надежный поставщик металлопроката. "
        "Используйте кнопки ниже, чтобы выбрать интересующий раздел."
    )
    await message.answer(text, reply_markup=kb.get_main_menu_keyboard())

# Main menu callback
@router.callback_query(F.data == "main_menu")
async def cq_main_menu(callback: CallbackQuery):
    text = (
        "<b>Главное меню</b>\n\n"
        "Выберите интересующий вас раздел."
    )
    await callback.message.edit_text(text, reply_markup=kb.get_main_menu_keyboard())
    await callback.answer()

# Show categories
@router.callback_query(F.data == "show_categories")
async def cq_show_categories(callback: CallbackQuery):
    if not get_all_categories():
        await callback.answer("Категории отсутствуют. Попробуйте позже.", show_alert=True)
        return
    text = "<b>Каталог товаров</b>\n\nВыберите категорию:"
    await callback.message.edit_text(text, reply_markup=kb.get_categories_keyboard())
    await callback.answer()

# Category details
@router.callback_query(F.data.startswith("category_"))
async def cq_category_details(callback: CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    details = get_category_details(category_id)
    if not details:
        await callback.answer("Категория не найдена.", show_alert=True)
        return
    text = (
        f"<b>{details['name']}</b>\n\n"
        f"Средняя цена за тонну: <b>{details['average_price']:,} руб.</b>\n\n"
        "Вы можете рассчитать точную стоимость вашего заказа."
    )
    await callback.message.edit_text(text, reply_markup=kb.get_category_details_keyboard(category_id))
    await callback.answer()

# Start calculation
@router.callback_query(F.data.startswith("calculate_"))
async def cq_start_calculation(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.set_state(CalculationStates.waiting_for_meters)
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("Введите необходимое количество метров:", reply_markup=kb.get_calculator_keyboard())
    await callback.answer()

# Process meters
@router.message(CalculationStates.waiting_for_meters)
async def process_meters(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Пожалуйста, введите корректное целое число больше 0.")
        return
    await state.update_data(meters=int(message.text))
    await state.set_state(CalculationStates.waiting_for_date)
    await message.answer("Когда вам необходима доставка? (например, 'завтра', 'в течение недели')")

# Process date and finish
@router.message(CalculationStates.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(delivery_date=message.text)
    data = await state.get_data()
    await state.clear()

    category_id = data.get("category_id")
    meters = data.get("meters")
    delivery_date = data.get("delivery_date")

    details = get_category_details(category_id)
    if not details:
        await message.answer("Ошибка: не удалось найти выбранную категорию.")
        return

    # Simple weight assumption – this should be replaced with real data
    weight_per_meter_kg = 10
    total_weight_ton = meters * weight_per_meter_kg / 1000
    total_cost = total_weight_ton * details["average_price"]

    # Notify manager
    manager_text = (
        f"<b>🔔 Новая заявка</b>\n\n"
        f"<b>Пользователь:</b> @{message.from_user.username} (ID: {message.from_user.id})\n"
        f"<b>Товар:</b> {details['name']}\n"
        f"<b>Количество:</b> {meters} м\n"
        f"<b>Примерный вес:</b> {total_weight_ton:.2f} т\n"
        f"<b>Примерная стоимость:</b> {total_cost:,.2f} руб.\n"
        f"<b>Срок поставки:</b> {delivery_date}"
    )
    try:
        await bot.send_message(config.MANAGER_CHANNEL_ID, manager_text)
    except Exception as e:
        logger.error(f"Failed to send message to manager channel: {e}")

    # Reply to user
    user_text = (
        f"<b>Ваша заявка принята!</b>\n\n"
        f"<b>Товар:</b> {details['name']}\n"
        f"<b>Количество:</b> {meters} м\n"
        f"<b>Примерная стоимость:</b> {total_cost:,.2f} руб.\n\n"
        "Наш менеджер свяжется с вами в ближайшее время."
    )
    await message.answer(user_text, reply_markup=kb.get_main_menu_keyboard())

# Contact manager
@router.callback_query(F.data == "contact_manager")
async def cq_contact_manager(callback: CallbackQuery, bot: Bot):
    user = callback.from_user
    manager_text = (
        f"<b>📞 Запрос на связь</b>\n\n"
        f"Пользователь @{user.username} (ID: {user.id}) просит связаться."
    )
    try:
        await bot.send_message(config.MANAGER_CHANNEL_ID, manager_text)
        await callback.answer("Ваш запрос отправлен. Менеджер скоро свяжется с вами.", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to send contact request: {e}")
        await callback.answer("Не удалось отправить запрос. Попробуйте позже.", show_alert=True) 