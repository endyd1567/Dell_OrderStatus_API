import sqlite3

# 데이터베이스 연결
DB_PATH = "orders.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 삽입할 데이터
order_number = "1014977567"
purchase_order_number = "OH-2501-KTCLOU"
product_description = "PowerEdge R760서버"
quantity = 2
box = "2"
today_date = "2025-02-07"

# 데이터 삽입 SQL 실행
cursor.execute('''
    INSERT INTO orders (order_number, purchase_order_number, product_description, quantity, box, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
''', (order_number, purchase_order_number, product_description, quantity, box, today_date))

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("✅ 데이터가 성공적으로 저장되었습니다!")
