import sqlite3

DB_PATH = "orders.db"

def remove_duplicate_orders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 중복 데이터를 찾아 첫 번째 ID만 유지하고 나머지는 삭제
    cursor.execute('''
        DELETE FROM orders
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM orders 
            GROUP BY order_number, product_description, created_at
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 중복 데이터 삭제 완료!")

# 실행
remove_duplicate_orders()
