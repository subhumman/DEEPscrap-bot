from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from keyboards import get_main_keyboard, get_services_keyboard, get_contact_keyboard
from parser import MetalParser
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Инициализируем парсер
parser = MetalParser()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    """
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Я бот для получения информации об услугах и ценах.\n"
        "Используйте команды:\n"
        "/services - список услуг\n"
        "/prices - текущие цены",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("services"))
async def cmd_services(message: types.Message):
    """
    Обработчик команды /services
    """
    logger.info(f"User {message.from_user.id} requested services list")
    try:
        # Получаем список услуг
        services = await parser.get_cached_services()
        logger.info(f"Retrieved {len(services) if services else 0} services")
        
        if not services:
            logger.warning("No services found")
            await message.answer(
                "❌ Не удалось получить список услуг. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
            return

        # Создаем клавиатуру с услугами
        keyboard = get_services_keyboard(services)
        await message.answer(
            "📋 Выберите услугу:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in cmd_services: {str(e)}", exc_info=True)
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )

@router.callback_query(F.data.startswith('service_'))
async def process_service_callback(callback_query: CallbackQuery):
    """
    Обработчик выбора услуги
    """
    service_name = callback_query.data.replace('service_', '')
    logger.info(f"User {callback_query.from_user.id} selected service: {service_name}")
    
    try:
        # Получаем среднюю цену
        avg_price = await parser.get_average_price(service_name)
        logger.info(f"Retrieved average price for {service_name}: {avg_price}")
        
        if avg_price:
            await callback_query.message.edit_text(
                f"💰 Средняя цена для услуги '{service_name}':\n"
                f"{avg_price:.2f} руб.",
                reply_markup=get_contact_keyboard()
            )
        else:
            logger.warning(f"No price found for service: {service_name}")
            await callback_query.message.edit_text(
                f"❌ Не удалось получить цену для услуги '{service_name}'",
                reply_markup=get_contact_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in process_service_callback: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_contact_keyboard()
        )
    finally:
        await callback_query.answer()

@router.callback_query(F.data == 'back_to_services')
async def process_back_callback(callback_query: CallbackQuery):
    """
    Обработчик возврата к списку услуг
    """
    logger.info(f"User {callback_query.from_user.id} returned to services list")
    try:
        services = await parser.get_cached_services()
        if not services:
            logger.warning("No services found when returning to list")
            await callback_query.message.edit_text(
                "❌ Не удалось получить список услуг. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
            return

        keyboard = get_services_keyboard(services)
        await callback_query.message.edit_text(
            "📋 Выберите услугу:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in process_back_callback: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    finally:
        await callback_query.answer()

@router.message(Command("prices"))
async def cmd_prices(message: types.Message):
    """
    Обработчик команды /prices
    """
    logger.info(f"User {message.from_user.id} requested prices")
    try:
        # Получаем список услуг и цен
        services = await parser.get_cached_services()
        logger.info(f"Retrieved {len(services) if services else 0} services for prices")
        
        if not services:
            logger.warning("No services found for prices")
            await message.answer(
                "❌ Не удалось получить цены. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
            return

        # Формируем сообщение с ценами
        prices_text = "📊 Текущие цены:\n\n"
        for service_name in services:
            avg_price = await parser.get_average_price(service_name)
            if avg_price:
                prices_text += f"{service_name}: {avg_price:.2f} руб.\n"
                logger.info(f"Added price for {service_name}: {avg_price}")

        await message.answer(
            prices_text,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in cmd_prices: {str(e)}", exc_info=True)
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        ) 