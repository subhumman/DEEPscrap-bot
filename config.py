from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

"""
класс для конфигурации
"""

@dataclass
class Config:
    BOT_TOKEN: str = '7853196472:AAGR56i67pY9Ug6N_xbi_tk10lsTi1-vGHQ'
    BASE_URL: str = "https://krasnodar.23met.ru/"

config = Config() 