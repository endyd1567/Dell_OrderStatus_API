import sqlite3

# 데이터베이스 경로
DB_PATH = "orders.db"

# 변경할 날짜
new_date = "2025-03-05"

# 변경할 주문번호 리스트 (order_id → order_number로 수정)
order_numbers = [1016031605]

try:
    # 데이터베이스 연결 및 실행
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 주문번호 리스트를 SQL IN 절에서 사용하기 위해 문자열 변환
        placeholders = ', '.join(['?'] * len(order_numbers))
        sql_query = f'''
            UPDATE orders
            SET created_at = ?
            WHERE order_number IN ({placeholders})
        '''

        # SQL 실행 (order_numbers를 파라미터로 전달)
        cursor.execute(sql_query, (new_date, *order_numbers))

        # 변경된 행 수 확인
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            print(f"✅ {updated_rows}개의 주문의 날짜가 {new_date}로 변경되었습니다.")
        else:
            print("⚠ 변경할 데이터가 없습니다.")

except sqlite3.Error as e:
    print(f"❌ 데이터 변경 중 오류 발생: {e}")
