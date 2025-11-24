import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
# 이 함수는 애플리케이션 시작 시 한 번만 호출되면 됩니다.
load_dotenv()

# =========================================================
# 1. 고정 설정 (Application & Database)
# =========================================================
DB_PATH = "orders.db"
ITEMS_PER_PAGE = 10
UPLOAD_FOLDER = 'uploads'

# =========================================================
# 2. Dell API 설정 (환경 변수에서 로드)
# =========================================================
API_URL = os.getenv("DELL_API_URL")
API_KEY = os.getenv("DELL_API_KEY")
SHARED_SECRET = os.getenv("DELL_SHARED_SECRET")
TOKEN_URL = os.getenv("DELL_TOKEN_URL")

# =========================================================
# 3. Email 설정 (환경 변수에서 로드)
# =========================================================
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# =========================================================
# 4. AWS 설정 (환경 변수에서 로드)
# =========================================================
SECRET_KEY = os.getenv("AWS_SECRET_KEY")

# =========================================================
# 5. 필수 변수 누락 확인
# =========================================================
# 필수 키 목록을 딕셔너리로 만들어, 누락 시 어떤 키가 문제인지 명확히 알 수 있도록 개선
REQUIRED_VARS = {
    "DELL_API_KEY": API_KEY, 
    "DELL_SHARED_SECRET": SHARED_SECRET, 
    "SENDER_PASSWORD": SENDER_PASSWORD,
    "AWS_SECRET_KEY": SECRET_KEY, # 새로 추가된 AWS SECRET_KEY
}

missing_vars = [name for name, value in REQUIRED_VARS.items() if value is None]

if missing_vars:
    # 누락된 변수 이름을 출력하고 프로그램 중단 (안전한 설정 로딩을 위해 권장)
    print(f"⚠️ 오류: .env 파일에서 다음 필수 환경 변수가 누락되었거나 비어 있습니다: {', '.join(missing_vars)}")
    # raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
