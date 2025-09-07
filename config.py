from dataclasses import dataclass, field
import os
from dotenv import load_dotenv
from pathlib import Path

# Явно указываем путь к .env и загружаем его
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True, encoding='utf-8')

# Отладочный вывод для проверки загрузки переменных
print('DEBUG: BOT_TOKEN from .env =', os.getenv('BOT_TOKEN'))

"""
класс для конфигурации
"""

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv('BOT_TOKEN')
    BASE_URL: str = os.getenv('BASE_URL', "URL")
    MANAGER_CHANNEL_ID: str = os.getenv('MANAGER_CHANNEL_ID')
    
    # Proxy configuration
    PROXIES: list = field(default_factory=lambda: [
        proxy for proxy in os.getenv('PROXIES', '').split(',') if proxy
    ])

    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is not set")
        if not self.MANAGER_CHANNEL_ID:
            raise ValueError("MANAGER_CHANNEL_ID environment variable is not set")


config = Config() 
