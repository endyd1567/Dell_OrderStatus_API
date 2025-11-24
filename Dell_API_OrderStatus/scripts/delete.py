import sqlite3

# 데이터베이스 경로
DB_PATH = "orders.db"

try:
    # 데이터베이스 연결 및 실행
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 삭제할 날짜
        delete_dates = ("2025-02-24", "2025-02-25")

        # 삭제 SQL 실행
        cursor.execute('''
            DELETE FROM orders
            WHERE created_at IN (?, ?)
        ''', delete_dates)

        # 변경된 행 수 확인
        deleted_rows = cursor.rowcount
        if deleted_rows > 0:
            print(f"✅ {deleted_rows}개의 데이터가 삭제되었습니다.")
        else:
            print("⚠ 삭제할 데이터가 없습니다.")

except sqlite3.Error as e:
    print(f"❌ 데이터 삭제 중 오류 발생: {e}")
