import hmac
import hashlib
import time
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# TODO: 본인의 쿠팡 파트너스 API 키로 변경하세요
ACCESS_KEY = "YOUR_ACCESS_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"

DOMAIN = "https://api-gateway.coupang.com"

def generate_hmac(method, url, secret_key, access_key):
    path, *query = url.split("?")
    query_string = query[0] if query else ""
    
    os_date = time.strftime('%y%m%d')
    gmt_date = time.strftime('%Y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'
    
    message = gmt_date + method + path + query_string
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    authorization = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={gmt_date}, signature={signature}"
    return authorization

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_products():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({"error": "검색어를 입력해주세요."}), 400

    # 쿠팡 파트너스 상품 검색 API 경로 (정렬 기준: 판매량순 또는 정확도순 등)
    # limit: 출력 개수 (최대 50개)
    path = f"/v2/providers/coupang_affiliate/apis/v1/products/search?keyword={requests.utils.quote(keyword)}&limit=10"
    url = DOMAIN + path
    
    authorization = generate_hmac("GET", path, SECRET_KEY, ACCESS_KEY)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)