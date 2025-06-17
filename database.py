import sqlite3
import logging
import ujson

# Настройка логирования
logger = logging.getLogger(__name__)

DB_FILE = 'metal_prices.db'

def execute_query(query: str, params: tuple = (), fetch: str = None):
    """
    Выполняет SQL-запрос к базе данных.

    Args:
        query (str): SQL-запрос.
        params (tuple): Параметры для запроса.
        fetch (str): Тип выборки ('one', 'all').
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            if fetch == 'one':
                return cursor.fetchone()
            if fetch == 'all':
                return cursor.fetchall()
            return None
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None

def init_db():
    """Инициализирует базу данных и создает таблицы, если они не существуют."""
    logger.info("Initializing database...")
    
    # Таблица для категорий
    execute_query("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL
        )
    """)

    # Таблица для цен
    execute_query("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            position TEXT,
            spec TEXT,
            dimensions TEXT,
            price_per_ton TEXT,
            price_per_item TEXT,
            supplier TEXT,
            phone TEXT,
            city TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    # Таблица для фильтров/размеров
    execute_query("""
        CREATE TABLE IF NOT EXISTS filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            filter_group TEXT,
            sizes TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)
    logger.info("Database initialized.")

def clear_db():
    """Очищает все таблицы в базе данных."""
    logger.info("Clearing database...")
    execute_query("DELETE FROM prices")
    execute_query("DELETE FROM filters")
    execute_query("DELETE FROM categories")
    logger.info("Database cleared.")

def save_parsed_data(data: list):
    """
    Сохраняет спарсенные данные в базу данных.
    Данные должны быть в формате, который возвращает MetalParser.parse_all.
    """
    logger.info(f"Saving {len(data)} categories to database...")
    clear_db()
    
    for category_data in data:
        category_name = category_data.get('category_name')
        category_url = category_data.get('url')

        # Сохраняем категорию и получаем ее ID
        execute_query(
            "INSERT INTO categories (name, url) VALUES (?, ?)",
            (category_name, category_url)
        )
        category_id_result = execute_query(
            "SELECT id FROM categories WHERE name = ?",
            (category_name,),
            fetch='one'
        )
        if not category_id_result:
            continue
        category_id = category_id_result[0]

        # Сохраняем фильтры
        for group, sizes in category_data.get('filters', {}).items():
            execute_query(
                "INSERT INTO filters (category_id, filter_group, sizes) VALUES (?, ?, ?)",
                (category_id, group, ujson.dumps(sizes))
            )

        # Сохраняем цены
        for price_info in category_data.get('prices', []):
            execute_query(
                """
                INSERT INTO prices (
                    category_id, position, spec, dimensions, price_per_ton,
                    price_per_item, supplier, phone, city
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_id,
                    price_info.get('position'),
                    price_info.get('spec'),
                    price_info.get('dimensions'),
                    price_info.get('price_per_ton'),
                    price_info.get('price_per_item'),
                    price_info.get('supplier'),
                    price_info.get('phone'),
                    price_info.get('city')
                )
            )
    logger.info("Data saved to database successfully.")

def get_all_categories():
    """Возвращает все категории из базы данных."""
    return execute_query("SELECT id, name FROM categories ORDER BY name", fetch='all')

def get_category_details(category_id: int):
    """Возвращает детали категории, включая фильтры и средние цены."""
    # Получаем информацию о категории
    category_info = execute_query("SELECT name, url FROM categories WHERE id = ?", (category_id,), fetch='one')
    if not category_info:
        return None

    # Получаем фильтры
    filters = execute_query("SELECT filter_group, sizes FROM filters WHERE category_id = ?", (category_id,), fetch='all')
    
    # Рассчитываем среднюю цену
    avg_price_result = execute_query(
        """
        SELECT AVG(CAST(REPLACE(price_per_ton, ' ', '') AS REAL))
        FROM prices
        WHERE category_id = ? AND price_per_ton != ''
        """,
        (category_id,),
        fetch='one'
    )
    avg_price = avg_price_result[0] if avg_price_result and avg_price_result[0] is not None else 0

    return {
        'name': category_info[0],
        'url': category_info[1],
        'filters': {group: ujson.loads(sizes) for group, sizes in filters},
        'average_price': round(avg_price, 2)
    }

if __name__ == '__main__':
    # Пример использования
    init_db()
    
    # Пример получения категорий
    categories = get_all_categories()
    if categories:
        print("Categories found:", len(categories))
        
        # Пример получения деталей для первой категории
        first_category_id = categories[0][0]
        details = get_category_details(first_category_id)
        print("\nDetails for first category:", details)
    else:
        print("No categories found in DB.") 