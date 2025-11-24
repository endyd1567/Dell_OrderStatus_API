from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import datetime
import logging
import smtplib
from email.mime.text import MIMEText

import config
import database
import dell_api
import ocr

# --- App Setup ---
app = Flask(__name__)
app.config.from_object(config)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Helper Functions ---

def _get_api_token():
    """Wrapper to get API token and handle failure gracefully."""
    try:
        return dell_api.get_access_token()
    except dell_api.TokenError as e:
        logging.error(f"Fatal: Could not obtain Dell API token. API lookups will fail. Error: {e}")
        return None

def _process_manual_orders(manual_order_numbers, boxes, token):
    """Helper function to process manually entered order numbers."""
    collected_data = []
    for i, manual_order_number in enumerate(manual_order_numbers):
        if not manual_order_number.strip():
            continue

        box_value = boxes[i] if i < len(boxes) else "N/A"
        logging.info(f"Processing manual order: {manual_order_number}")

        if not token:
            order_details = {"purchase_order_number": "API 토큰 실패", "order_number": manual_order_number, "products": [], "box": box_value}
            collected_data.append(order_details)
            continue
        try:
            order_data = dell_api.fetch_order_data([manual_order_number], token)
            order_details = dell_api.extract_order_details(manual_order_number, order_data)
            order_details["box"] = box_value
            collected_data.append(order_details)
            logging.info(f"✅ Successfully processed manual order: {manual_order_number}")
        except dell_api.OrderFetchError as e:
            logging.error(f"❌ Dell API error for manual order {manual_order_number}: {e}")
            order_details = {"purchase_order_number": "API 조회 실패", "order_number": manual_order_number, "products": [], "box": box_value}
            collected_data.append(order_details)
        except Exception as e:
            logging.error(f"❌ Unexpected error for manual order {manual_order_number}: {e}", exc_info=True)
            order_details = {"purchase_order_number": "알 수 없는 오류", "order_number": manual_order_number, "products": [], "box": box_value}
            collected_data.append(order_details)
            
    return collected_data

def _process_uploaded_files(files, token):
    """Helper function to process uploaded image files. Returns data and errors."""
    collected_data = []
    errors = []

    for file in files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(file_path)
            logging.info(f"Processing file: {filename}")
            
            ocr_results = ocr.extract_order_details_from_image(file_path)

            if not ocr_results:
                logging.error(f"❌ OCR did not find any order numbers in {filename}")
                errors.append(f"'{filename}'에서 주문 번호를 찾지 못했습니다. 이미지를 확인 후 다시 시도하거나 수동으로 입력해주세요.")
                continue

            for ocr_result in ocr_results:
                if ocr_result.get("error"):
                    error_msg = ocr_result.get("error")
                    logging.error(f"❌ OCR failed for {filename}: {error_msg}")
                    errors.append(f"'{filename}' 이미지 처리 실패: {error_msg}")
                    continue

                order_number = ocr_result.get("order_number")
                box = ocr_result.get("box", "N/A")

                if order_number:
                    logging.info(f"✅ OCR successful for {filename}. Order: {order_number}. Querying Dell API...")
                    if not token:
                        order_details = {"purchase_order_number": "API 토큰 실패", "order_number": order_number, "products": [], "box": box}
                    else:
                        try:
                            order_data = dell_api.fetch_order_data([order_number], token)
                            order_details = dell_api.extract_order_details(order_number, order_data)
                            order_details["box"] = box
                            logging.info(f"✅ Dell API query successful for order: {order_number}")
                        except dell_api.OrderFetchError as e:
                            logging.error(f"❌ Dell API error for {filename} (Order: {order_number}): {e}")
                            order_details = {"purchase_order_number": "API 조회 실패", "order_number": order_number, "products": [], "box": box}
                    collected_data.append(order_details)
                else:
                    # This case handles if a result in the list is missing an order number
                    logging.warning(f"⚠️ OCR result for {filename} is missing an order number.")
                    # Optionally, add a less severe error message
                    # errors.append(f"'{filename}'의 일부 항목에서 주문 번호를 찾지 못했습니다.")

        except Exception as e:
            logging.error(f"❌ Critical error processing file {filename}: {e}", exc_info=True)
            errors.append(f"'{filename}' 처리 중 예상치 못한 오류 발생: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    return collected_data, errors

def _group_orders(db_rows):
    """Groups database rows by order_number and aggregates their products."""
    grouped_orders = {}
    for row in db_rows:
        row_dict = dict(row)
        order_num = row_dict['order_number']
        
        if order_num not in grouped_orders:
            grouped_orders[order_num] = {
                "order_number": order_num,
                "purchase_order_number": row_dict['purchase_order_number'],
                "created_at": row_dict['created_at'],
                "shipped": row_dict['shipped'],
                "memo": row_dict['memo'],
                "box": row_dict['box'],
                "products": []
            }
        
        grouped_orders[order_num]['products'].append({
            "description": row_dict['product_description'],
            "itemQuantity": row_dict['quantity']
        })
        
    return list(grouped_orders.values())

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/product_scan.html')
def product_scan():
    session.pop('collected_data', None)
    return render_template('product_scan.html')

@app.route('/process_order', methods=['POST'])
def process_order():
    session.pop('collected_data', None)
    all_collected_data = []
    token = _get_api_token()

    files = request.files.getlist('files[]')
    manual_order_numbers = request.form.getlist("manual_order_numbers[]")
    has_files = files and any(f.filename for f in files)
    has_manual_orders = any(m.strip() for m in manual_order_numbers)

    if not has_files and not has_manual_orders:
        return jsonify({"status": "error", "message": "처리할 데이터가 없습니다. 파일을 업로드하거나 주문 번호를 수동으로 입력하세요."}), 400

    # --- Process Files ---
    if has_files:
        file_data, file_errors = _process_uploaded_files(files, token)
        if file_errors:
            return jsonify({"status": "error", "errors": file_errors})
        all_collected_data.extend(file_data)

    # --- Process Manual Orders ---
    if has_manual_orders:
        boxes = request.form.getlist("box[]")
        manual_data = _process_manual_orders(manual_order_numbers, boxes, token)
        all_collected_data.extend(manual_data)
    
    if not all_collected_data:
        return jsonify({"status": "error", "message": "처리할 데이터가 없습니다. 파일을 업로드하거나 주문 번호를 수동으로 입력하세요."}), 400

    session['collected_data'] = all_collected_data
    session.modified = True
    
    return jsonify({"status": "success", "redirect_url": url_for('results_page')})

@app.route('/results')
def results_page():
    orders = session.get('collected_data', [])
    if not orders:
        return render_template('result.html', message="처리된 데이터가 없습니다. 다시 시도해주세요.")
    return render_template('result.html', orders=orders)

@app.route('/save_orders', methods=['POST'])
def save_orders_route():
    orders = session.get('collected_data', [])
    if not orders:
        return jsonify({"message": "저장할 데이터가 없습니다."}), 400
    
    saved_count = database.save_orders(orders)
    session.pop('collected_data', None)
    
    return jsonify({"message": f"{saved_count}개의 새로운 항목이 성공적으로 저장되었습니다."}), 200

def get_week_range(date_str):
    """Get the Sunday and Saturday of the week for a given date string."""
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    start_of_week = date - datetime.timedelta(days=(date.weekday() + 1) % 7)  # Sunday
    end_of_week = start_of_week + datetime.timedelta(days=6)  # Saturday
    return start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')

@app.route('/order_list', methods=['GET'])
def order_list():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # If no date range is provided, find the latest date and show just that day's orders.
    if not start_date or not end_date:
        latest_date = database.get_latest_date() or datetime.date.today().strftime('%Y-%m-%d')
        # Set both start and end to the latest date to show only that day.
        start_date = latest_date
        end_date = latest_date
        return redirect(url_for('order_list', start_date=start_date, end_date=end_date))

    # Fetch and group orders for the given date range.
    # Note: The search routes handle their own pagination. This route shows all items in the range.
    db_orders = database.get_orders_by_date_range(start_date, end_date)
    order_list = _group_orders(db_orders)
    
    return render_template(
        'product_list.html',
        orders=order_list,
        start_date=start_date,
        end_date=end_date,
        available_dates=database.get_all_dates()
    )

@app.route('/search', methods=['GET'])
def search_orders():
    """Search orders by a specific field and value with pagination."""
    page = int(request.args.get('page', 1))
    field = request.args.get('field')
    value = request.args.get('value')
    
    if not field or not value:
        return redirect(url_for('search_all'))

    query = f"WHERE {field} LIKE ?"
    params = [f"%{value}%"]
    
    all_orders_flat = database.get_all_orders_matching(query, params)
    all_grouped_orders = _group_orders(all_orders_flat)
    
    total_items = len(all_grouped_orders)
    total_pages = (total_items + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE if total_items > 0 else 1
    start_index = (page - 1) * config.ITEMS_PER_PAGE
    end_index = start_index + config.ITEMS_PER_PAGE
    paginated_orders = all_grouped_orders[start_index:end_index]
    
    return render_template(
        'product_list.html',
        orders=paginated_orders,
        selected_field=field,
        search_value=value,
        page=page,
        total_pages=total_pages
    )

@app.route('/search_all', methods=['GET'])
def search_all():
    """Retrieve all orders with pagination."""
    page = int(request.args.get('page', 1))
    
    all_orders_flat = database.get_all_orders_matching()
    all_grouped_orders = _group_orders(all_orders_flat)

    total_items = len(all_grouped_orders)
    total_pages = (total_items + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE if total_items > 0 else 1
    start_index = (page - 1) * config.ITEMS_PER_PAGE
    end_index = start_index + config.ITEMS_PER_PAGE
    paginated_orders = all_grouped_orders[start_index:end_index]

    return render_template(
        'product_list.html',
        orders=paginated_orders,
        selected_filter="all",
        page=page,
        total_pages=total_pages
    )

@app.route('/search_unshipped', methods=['GET'])
def search_unshipped():
    """Retrieve all unshipped orders with pagination."""
    page = int(request.args.get('page', 1))
    query = "WHERE shipped = 0"
    
    all_orders_flat = database.get_all_orders_matching(query)
    all_grouped_orders = _group_orders(all_orders_flat)

    total_items = len(all_grouped_orders)
    total_pages = (total_items + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE if total_items > 0 else 1
    start_index = (page - 1) * config.ITEMS_PER_PAGE
    end_index = start_index + config.ITEMS_PER_PAGE
    paginated_orders = all_grouped_orders[start_index:end_index]

    return render_template(
        'product_list.html',
        orders=paginated_orders,
        selected_filter="unshipped",
        page=page,
        total_pages=total_pages
    )

@app.route('/search_shipped', methods=['GET'])
def search_shipped():
    """Retrieve all shipped orders with pagination."""
    page = int(request.args.get('page', 1))
    query = "WHERE shipped = 1"

    all_orders_flat = database.get_all_orders_matching(query)
    all_grouped_orders = _group_orders(all_orders_flat)

    total_items = len(all_grouped_orders)
    total_pages = (total_items + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE if total_items > 0 else 1
    start_index = (page - 1) * config.ITEMS_PER_PAGE
    end_index = start_index + config.ITEMS_PER_PAGE
    paginated_orders = all_grouped_orders[start_index:end_index]

    return render_template(
        'product_list.html',
        orders=paginated_orders,
        selected_filter="shipped",
        page=page,
        total_pages=total_pages
    )

@app.route('/update_shipped_status', methods=['POST'])
def update_shipped_status_route():
    order_number = request.form.get('order_number')
    shipped_status = request.form.get('shipped')
    if not order_number:
        return jsonify({"error": "주문 번호가 없습니다."}), 400

    shipped_value = database.update_shipped_status(order_number, shipped_status)
    return jsonify({"message": "출고 상태가 업데이트되었습니다.", "shipped": shipped_value})

@app.route('/update_memo', methods=['POST'])
def update_memo_route():
    order_number = request.form.get('order_number')
    memo = request.form.get('memo', '')
    if not order_number:
        return jsonify({"error": "주문 번호가 없습니다."}), 400

    database.update_memo(order_number, memo)
    return jsonify({"message": "메모 저장 완료"})

@app.route('/notify_admin', methods=['POST'])
def notify_admin():
    try:
        msg = MIMEText(f"입고 스캔 처리 중 문제가 발생하여 호출드립니다.\n\n"
                       f"요청자 IP: {request.remote_addr}\n"
                       f"시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        msg['Subject'] = "📡 입고 시스템 관리자 호출"
        msg['From'] = app.config['SENDER_EMAIL']
        msg['To'] = app.config['ADMIN_EMAIL']

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(app.config['SENDER_EMAIL'], app.config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        return jsonify({"message": "관리자에게 메일이 전송되었습니다."})
    except Exception as e:
        logging.error(f"메일 전송 실패: {e}", exc_info=True)
        return jsonify({"error": "메일 전송에 실패했습니다. 서버 로그를 확인해주세요."}), 500

# --- Main Execution ---

if __name__ == '__main__':
    # Set werkzeug logger level
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.INFO)
    app.run(host='0.0.0.0', port=5000, debug=False)
