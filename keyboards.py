from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from typing import List

from database import get_all_categories

def get_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает основную клавиатуру
    """
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Список услуг", callback_data="show_services"),
            InlineKeyboardButton(text="💰 Цены", callback_data="show_prices")
        ],
        [
            InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_services_keyboard(services: list) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком услуг
    """
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📋 {service}",
                callback_data=f"service_{service}"
            )
        ])
    
    # Добавляем кнопку возврата в главное меню
    keyboard.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Связь с менеджером'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Связь с менеджером", callback_data="contact_manager")
    return builder.as_markup()

# --- Главное меню ---

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру главного меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Товары", callback_data="show_categories")
    builder.button(text="📞 Связь с менеджером", callback_data="contact_manager")
    builder.adjust(1)
    return builder.as_markup()

# --- Категории товаров ---

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком категорий товаров."""
    categories = get_all_categories()
    builder = InlineKeyboardBuilder()

    for category_id, name in categories:
        builder.button(text=name, callback_data=f"category_{category_id}")
    
    builder.button(text="« Назад", callback_data="main_menu")
    
    # Распределяем кнопки по 2 в ряд, последняя ('Назад') будет в своем ряду
    builder.adjust(*([2] * (len(categories) // 2)), 1)
    return builder.as_markup()

# --- Детали категории ---

def get_category_details_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для страницы с деталями категории."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🧮 Посчитать стоимость", callback_data=f"calculate_{category_id}")
    builder.button(text="« Назад к товарам", callback_data="show_categories")
    builder.button(text="📞 Связь с менеджером", callback_data="contact_manager")
    builder.adjust(1)
    return builder.as_markup()

# --- Калькулятор ---

def get_calculator_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены или возврата из калькулятора."""
    builder = InlineKeyboardBuilder()
    builder.button(text="« Назад к товарам", callback_data="show_categories")
    return builder.as_markup() 