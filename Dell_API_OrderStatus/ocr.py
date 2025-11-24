import boto3
from botocore.exceptions import BotoCoreError, ClientError
import re
import logging
from collections import Counter

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# AWS Textract 클라이언트 초기화
textract_client = boto3.client('textract', region_name='ap-northeast-2')

def extract_order_details_from_image(image_path):
    """
    Amazon Textract를 사용하여 이미지에서 주문 세부 정보를 추출합니다.
    '납품확인서' 형식의 여러 주문 번호와 기존 라벨의 단일 주문 번호를 모두 처리합니다.
    결과는 항상 사전 목록으로 반환됩니다.
    """
    logging.info(f"Starting OCR process for image: {image_path}")
    try:
        with open(image_path, 'rb') as document:
            image_bytes = document.read()

        if not image_bytes:
            logging.error("Image file is empty.")
            return [{"error": "Image file is empty."}]

        response = textract_client.detect_document_text(Document={'Bytes': image_bytes})
        
        blocks = response.get('Blocks', [])
        if not blocks:
            logging.warning("Textract did not detect any text blocks.")
            return [{"error": "No text detected in image."}]

        lines = [block['Text'] for block in blocks if block.get('BlockType') == 'LINE']
        full_text = " ".join(lines)
        logging.info(f"Extracted text: '{full_text}'")

        # --- 다중 주문 추출 (납품확인서 형식) ---
        if "ORDER#" in full_text:
            results = []
            logging.info("납품확인서 형식을 감지했습니다. 다중 주문 추출을 시도합니다.")
            for line in lines:
                # 라인에서 9자리 또는 10자리 주문 번호 탐색
                order_match = re.search(r'\b([0-9]{9,10})\b', line)
                if order_match:
                    order_number = order_match.group(1)
                    
                    # 같은 라인에서 박스 번호(1~3자리 숫자) 탐색
                    box_match = re.search(r'(Box|박스)\s*[:\s]*(\d{1,3})\b', line, re.IGNORECASE)
                    box_number = box_match.group(2) if box_match else None
                    
                    # 'Box' 키워드가 없는 경우, 주문 번호가 아닌 다른 숫자를 박스 번호로 간주
                    if not box_number:
                        other_numbers = re.findall(r'\b(\d+)\b', line)
                        for num in other_numbers:
                            if num != order_number:
                                box_number = num
                                break # 첫 번째로 일치하는 다른 숫자를 박스 번호로 사용

                    results.append({"order_number": order_number, "box": box_number})
            
            if results:
                logging.info(f"납품확인서에서 {len(results)}개의 주문을 찾았습니다.")
                return results

        # --- 단일 주문 추출 (기존 라벨 형식) ---
        logging.info("단일 주문 추출 로직을 사용합니다.")
        order_number = None
        
        # 1. "Order No" 패턴
        match = re.search(r"Order\s*No[:.\s#]*([0-9]{9,10})\b", full_text, re.IGNORECASE)
        if match:
            order_number = match.group(1)
            logging.info(f"패턴 'Order No'를 사용하여 주문 번호를 찾았습니다: {order_number}")
        
        # 2. 가장 흔한 10자리 숫자 (Fallback)
        if not order_number:
            all_10_digit_numbers = re.findall(r"\b([0-9]{10})\b", full_text)
            if all_10_digit_numbers:
                counts = Counter(all_10_digit_numbers)
                most_common = counts.most_common(1)
                if most_common and most_common[0][1] > 0:
                    order_number = most_common[0][0]
                    logging.info(f"가장 흔한 10자리 숫자를 주문 번호로 찾았습니다: {order_number}")

        if not order_number:
            logging.warning("모든 패턴 시도 후에도 주문 번호를 찾지 못했습니다.")
        
        # --- Box 번호 추출 ---
        box = None
        match = re.search(r"(?:of|\/)\s*([0-9]+)\b", full_text, re.IGNORECASE)
        if match:
            box = match.group(1)
            logging.info(f"패턴 'of Y'를 사용하여 Box 번호를 찾았습니다: {box}")
        else:
            match = re.search(r"Box\s*([0-9]+)\b", full_text, re.IGNORECASE)
            if match:
                box = match.group(1)
                logging.info(f"패턴 'Box Y'를 사용하여 Box 번호를 찾았습니다: {box}")
        
        box_num = None
        if box:
            try:
                box_num = int(box)
                logging.info(f"최종 Box 번호: {box_num}")
            except ValueError:
                logging.warning(f"추출된 box 값 '{box}'는 유효한 정수가 아닙니다.")
        
        if not order_number:
            return [] # 아무것도 찾지 못하면 빈 리스트 반환

        return [{"order_number": order_number, "box": box_num}]

    except (BotoCoreError, ClientError) as e:
        logging.error(f"AWS Textract API 오류: {e}", exc_info=True)
        return [{"error": f"AWS Textract API 오류: {e}"}]
    except FileNotFoundError:
        logging.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        return [{"error": "파일을 찾을 수 없습니다"}]
    except Exception as e:
        logging.error(f"이미지 처리 중 예상치 못한 오류 발생: {e}", exc_info=True)
        return [{"error": "이미지 처리 중 예상치 못한 오류가 발생했습니다"}]
