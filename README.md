# Dell 장비 입고 관리 시스템

이 프로젝트는 Dell 장비의 입고 과정을 자동화하고 효율적으로 관리하기 위해 개발된 웹 애플리케이션입니다. OCR 기술을 활용하여 박스 라벨이나 납품 확인서의 주문 정보를 자동으로 추출하고, Dell API와 연동하여 상세 정보를 가져와 데이터베이스에 저장 및 관리합니다.

## 🌟 개발 이유 (Purpose)

수작업으로 진행되던 Dell 장비의 입고 및 재고 관리 과정에는 많은 시간과 노력이 소요되며, 데이터 오입력의 위험이 존재합니다. 이 시스템은 이러한 비효율을 개선하고, 아래와 같은 목표를 달성하기 위해 개발되었습니다.

- **자동화된 데이터 입력**: OCR을 통해 사진 속 텍스트를 자동으로 인식하여 수작업을 최소화합니다.
- **정확성 향상**: Dell API를 통해 공식적인 주문 정보를 조회하여 데이터의 정확성을 보장합니다.
- **효율적인 관리**: 모든 입고 내역을 데이터베이스에 기록하고, 강력한 조회 및 검색 기능을 통해 원하는 정보를 쉽고 빠르게 찾을 수 있도록 합니다.
- **업무 간소화**: 입고 처리부터 결과 메일 발송, 데이터 저장까지 이어지는 워크플로우를 간소화합니다.

## ✨ 주요 기능 (Key Features)

- **OCR 기반 자동 입고**: 박스 라벨(단일 주문) 또는 납품 확인서(다중 주문) 사진을 업로드하여 주문 정보를 자동으로 인식합니다.
- **Dell API 연동**: 추출된 주문 번호로 Dell API를 조회하여 정확한 제품 설명, 수량 등 상세 정보를 확인합니다.
- **수동 입력 지원**: 사진 인식이 어렵거나 시드 장비인 경우를 대비하여, 수동으로 주문 번호와 박스 정보를 입력할 수 있습니다.
- **데이터베이스 저장**: 처리된 모든 입고 내역을 로컬 SQLite 데이터베이스에 저장하여 영속적으로 관리합니다.
- **입고 내역 조회 및 검색**: 날짜별, 출고 상태별(전체/출고/미출고), 키워드별(주문번호, 제품명 등)로 입고 내역을 손쉽게 조회하고 검색할 수 있습니다.
- **상태 관리**: 각 주문에 대해 '출고' 상태를 체크박스로 변경하고, 관련 '메모'를 실시간으로 추가/수정할 수 있습니다.
- **사용자 친화적 UI**: 직관적인 인터페이스와 사진 업로드 양식 안내 팝업 등을 통해 누구나 쉽게 사용할 수 있습니다.

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap, jQuery, FullCalendar
- **Database**: SQLite
- **OCR**: AWS Textract
- **API Integration**: Dell Order and Shipment Status API

## 🚀 설치 및 실행 방법 (Installation and Setup)

1.  **리포지토리 복제:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **가상 환경 생성 및 활성화:**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **필요 라이브러리 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **`.env` 파일 설정:**
    프로젝트 루트 디렉터리에 `.env` 파일을 생성하고, 아래 형식에 맞게 필요한 환경 변수를 입력합니다.
    ```env
    # Dell API Credentials
    DELL_API_URL="https://apigtwb2c.us.dell.com/..."
    DELL_API_KEY="YOUR_DELL_API_KEY"
    DELL_SHARED_SECRET="YOUR_DELL_SHARED_SECRET"
    DELL_TOKEN_URL="https://apigtwb2c.us.dell.com/auth/oauth/v2/token"

    # AWS Credentials (for Textract)
    AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY"
    AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY"
    AWS_DEFAULT_REGION="ap-northeast-2" # or your preferred region

    # Email Settings (for Admin Notification)
    ADMIN_EMAIL="admin@example.com"
    SENDER_EMAIL="your-gmail-account@gmail.com"
    SENDER_PASSWORD="your-gmail-app-password"

    # Flask Secret Key
    SECRET_KEY="your-strong-secret-key"
    ```

5.  **애플리케이션 실행:**
    ```bash
    python app.py
    ```

6.  **접속**: 웹 브라우저에서 `http://127.0.0.1:5001` 주소로 접속합니다.

## 📖 사용 방법 (How to Use)

### 1. 입고 스캔
- 메인 페이지에서 **"입고 스캔"** 버튼을 클릭합니다.
- **"라벨 사진 업로드"** 섹션에서 "파일 선택"을 눌러 박스 라벨 또는 납품 확인서 사진을 업로드합니다.
  - "? 사진 양식" 버튼을 눌러 업로드 가능한 사진 예시를 확인할 수 있습니다.
- 또는 **"수동 주문 번호 입력"** 섹션에 직접 주문 번호와 박스 정보를 입력합니다.
- **"제출"** 버튼을 누르면 OCR 및 Dell API 조회가 실행되고, 결과 확인 페이지로 이동합니다.
- 결과 페이지에서 **"메일 보내기"** 버튼을 누르고, 팝업창에서 **"확인"**을 선택하면 입고 내역이 서버 데이터베이스에 최종 저장됩니다.

### 2. 입고 내역 조회
- 메인 페이지에서 **"날짜별 입고 장비 조회"** 버튼을 클릭합니다.
- 초기 화면에는 가장 최근에 입고된 날짜의 데이터가 표시됩니다.
- 상단의 캘린더에서 특정 날짜나 주(week)를 드래그하여 해당 기간의 데이터를 조회할 수 있습니다.
- 필터 버튼(**"모든 제품 조회"**, **"출고 제품 조회"**, **"미출고 제품 조회"**)을 통해 출고 상태별로 데이터를 필터링할 수 있습니다.
- '검색 필드'와 '검색 값'을 입력하여 특정 주문을 검색할 수 있습니다.

## 🌱 향후 개선 사항 (Future Improvements)

- **OCR 정확도 향상**: 납품 확인서와 같이 테이블 형태의 문서 인식을 위해, AWS Textract의 'Table Analysis' 기능을 도입하여 필드(Order#, Box 등)를 더 구조적으로 분석하고 정확도를 높일 수 있습니다.
- **사용자 인증**: 로그인 기능을 추가하여 허가된 사용자만 시스템에 접근할 수 있도록 보안을 강화합니다.
- **고급 리포팅**: 입고 통계, 장비별 재고 현황 등 다양한 분석 데이터를 시각화하여 리포팅하는 기능을 추가합니다.
