from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config
from typing import List

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
    """
    Создает клавиатуру с контактной информацией
    """
    keyboard = [
        [
            InlineKeyboardButton(text="📞 Позвонить", url="tel:+89897453695"),
        ],
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 