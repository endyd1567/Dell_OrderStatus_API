import requests
import logging
from config import API_KEY, SHARED_SECRET, TOKEN_URL, API_URL

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Custom Exceptions ---
class DellApiError(Exception):
    """Base exception for Dell API related errors."""
    pass

class TokenError(DellApiError):
    """Raised when the access token cannot be obtained."""
    pass

class OrderFetchError(DellApiError):
    """Raised when order data cannot be fetched."""
    pass

# --- Constants ---
SEED_EQUIPMENT_DETAILS = {
    "purchase_order_number": "시드 장비(주문 조회 불가)",
    "order_number": None,  # To be populated at runtime
    "products": [{"description": " ", "itemQuantity": " "}],
    "box": " "
}

def get_access_token():
    """OAuth 2.0 인증을 통해 Access Token 가져오기"""
    payload = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': SHARED_SECRET
    }
    logging.info(f"Requesting Access Token from URL: {TOKEN_URL}")
    try:
        response = requests.post(TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        access_token = response.json().get('access_token')
        if not access_token:
            raise TokenError("Access token not found in the response.")
        logging.info("✅ Access Token successfully obtained.")
        return access_token
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Access Token request failed: {e}")
        if e.response is not None:
            logging.error(f"  - Response content: {e.response.text}")
        raise TokenError("Failed to get access token due to a network error or invalid credentials.") from e

def fetch_order_data(order_numbers, access_token): 
    """주문 데이터 가져오기"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "SearchParameter": [
            {"key": "order_numbers", "values": order_numbers},
            {"key": "country_code", "values": ["KR"]}
        ]
    }
    logging.info(f"Requesting order data from Dell API for orders: {order_numbers}")
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info("✅ Successfully received data from Dell API.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Dell API request failed: {e}")
        if e.response is not None:
            logging.error(f"  - Response status code: {e.response.status_code}")
            logging.error(f"  - Response content: {e.response.text}")
        raise OrderFetchError(f"Failed to fetch order data for {order_numbers}.") from e

def extract_order_details(order_number, order_data):
    """주문 데이터에서 필요한 세부 정보를 추출하고 동일한 Description의 수량 합산"""
    logging.info(f"Extracting order details for order number: {order_number}")
    
    if not order_data or not order_data.get('purchaseOrderDetails'):
        logging.warning("⚠️ 'purchaseOrderDetails' not in response or data is empty. Treating as seed equipment.")
        details = SEED_EQUIPMENT_DETAILS.copy()
        details["order_number"] = order_number
        return details

    product_summary = {}
    purchase_order_number = "N/A"
    
    for purchase_order in order_data.get('purchaseOrderDetails', []):
        purchase_order_number = purchase_order.get('purchaseOrderNumber', purchase_order_number)
        for order in purchase_order.get('dellOrders', []):
            if order.get('orderNumber') == order_number:
                logging.info(f"Found matching order: {order_number}. Processing product information.")
                for product in order.get('productInfo', []):
                    description = product.get('description', 'Unknown Product')
                    try:
                        quantity = int(product.get('itemQuantity', 0))
                    except (ValueError, TypeError):
                        quantity = 0
                    product_summary[description] = product_summary.get(description, 0) + quantity

    if not product_summary:
        logging.warning("⚠️ No product information found for this order.")

    extracted_details = {
        "order_number": order_number,
        "purchase_order_number": purchase_order_number,
        "products": [
            {"description": desc, "itemQuantity": qty} for desc, qty in product_summary.items()
        ] if product_summary else [{"description": "제품 정보 없음", "itemQuantity": 0}]
    }
    logging.info(f"✅ Order details extracted successfully: {extracted_details}")
    return extracted_details
