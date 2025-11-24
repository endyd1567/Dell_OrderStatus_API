import sqlite3
import datetime
import logging
from contextlib import contextmanager
from config import DB_PATH, ITEMS_PER_PAGE

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@contextmanager
def get_db_connection():
    """데이터베이스 연결을 위한 컨텍스트 관리자를 제공합니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}", exc_info=True)
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def init_db():
    """데이터베이스가 없으면 생성하고, 테이블을 초기화합니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT NOT NULL,
                    purchase_order_number TEXT,
                    product_description TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    box TEXT,
                    created_at DATE DEFAULT (DATE('now')),
                    shipped INTEGER DEFAULT 0,
                    memo TEXT DEFAULT ''
                )
            ''')
            # Add index for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders (order_number);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON orders (created_at);')
            conn.commit()
        logging.info("✅ SQLite database and table initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize database: {e}", exc_info=True)

def update_database_schema():
    """기존 데이터베이스 스키마를 업데이트합니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(orders)")
            columns = [row['name'] for row in cursor.fetchall()]

            if 'shipped' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN shipped INTEGER DEFAULT 0")
                logging.info("✅ 'shipped' column added.")

            if 'memo' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN memo TEXT DEFAULT ''")
                logging.info("✅ 'memo' column added.")
            
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update database schema: {e}", exc_info=True)

def save_orders(orders):
    """주문 목록을 데이터베이스에 저장합니다. 중복된 항목은 건너뜁니다."""
    if not orders:
        return 0

    today_date = datetime.date.today().strftime('%Y-%m-%d')
    saved_count = 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for order in orders:
                # 데이터 유효성 검사
                order_number = order.get('order_number')
                if not order_number or 'products' not in order:
                    logging.warning(f"Skipping invalid order data: {order}")
                    continue

                for product in order['products']:
                    description = product.get('description')
                    quantity = product.get('itemQuantity')

                    # 중복 확인
                    cursor.execute(
                        "SELECT id FROM orders WHERE order_number = ? AND product_description = ? AND created_at = ?",
                        (order_number, description, today_date)
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(
                            "INSERT INTO orders (order_number, purchase_order_number, product_description, quantity, box, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (order_number, order.get('purchase_order_number'), description, quantity, order.get('box'), today_date)
                        )
                        saved_count += 1
            conn.commit()
        logging.info(f"Successfully saved {saved_count} new order items.")
    except sqlite3.Error as e:
        logging.error(f"Failed to save orders: {e}", exc_info=True)
        return 0
    return saved_count

def get_all_orders_matching(query="", params=()):
    """검색 조건과 일치하는 모든 주문을 가져옵니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            select_query = f"SELECT * FROM orders {query} ORDER BY created_at DESC, id DESC"
            cursor.execute(select_query, params)
            # 결과를 사전 목록으로 변환하여 반환
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all matching orders: {e}", exc_info=True)
        return []

def update_shipped_status(order_number, shipped_status):
    """주문의 출고 상태를 업데이트합니다."""
    shipped_value = 1 if shipped_status == "true" else 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET shipped = ? WHERE order_number = ?", (shipped_value, order_number))
            conn.commit()
        logging.info(f"Updated shipped status for order {order_number} to {shipped_value}")
        return shipped_value
    except sqlite3.Error as e:
        logging.error(f"Failed to update shipped status for order {order_number}: {e}", exc_info=True)
        return -1 # Indicate error

def update_memo(order_number, memo):
    """주문의 메모를 업데이트합니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET memo = ? WHERE order_number = ?", (memo, order_number))
            conn.commit()
        logging.info(f"Updated memo for order {order_number}")
    except sqlite3.Error as e:
        logging.error(f"Failed to update memo for order {order_number}: {e}", exc_info=True)

# --- One-off Functions (can be run manually if needed) ---

def get_all_dates():
    """주문이 존재하는 모든 날짜를 가져옵니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT created_at FROM orders ORDER BY created_at ASC")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all dates: {e}", exc_info=True)
        return []

def get_orders_by_date_range(start_date, end_date):
    """지정된 날짜 범위의 주문을 가져옵니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM orders WHERE DATE(created_at) BETWEEN DATE(?) AND DATE(?) ORDER BY created_at DESC, id DESC",
                (start_date, end_date)
            )
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Failed to get orders by date range: {e}", exc_info=True)
        return []

def get_latest_date():
    """가장 최신 주문 날짜를 가져옵니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(created_at) FROM orders")
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get latest date: {e}", exc_info=True)
        return None

# Initialize database on application start
init_db()
update_database_schema()
