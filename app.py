from flask import Flask, request, jsonify
from flask_cors import CORS
import FinanceDataReader as fdr
import numpy as np
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

@app.route('/api/predict', methods=['POST'])
def predict_stock():
    try:
        # 요청 데이터 로깅
        print("Request received:", request.json)
        
        stock_code = request.json.get('stockCode')
        if not stock_code:
            return jsonify({"error": "종목 코드가 필요합니다."}), 400

        # KRX 데이터 가져오기
        krx = fdr.StockListing('KRX')
        
        # 종목 찾기
        if stock_code.isdigit():
            stock_info = krx[krx['Code'] == stock_code]
        else:
            stock_info = krx[krx['Name'].str.contains(stock_code, case=False, na=False)]

        if stock_info.empty:
            return jsonify({"error": "종목을 찾을 수 없습니다."}), 404

        # 주식 데이터 가져오기
        code = stock_info.iloc[0]['Code']
        name = stock_info.iloc[0]['Name']
        
        # 최근 30일 데이터
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        df = fdr.DataReader(code, start_date.strftime('%Y-%m-%d'))

        if df.empty:
            return jsonify({"error": "주가 데이터를 가져올 수 없습니다."}), 404

        # 현재가 및 예측가격 계산
        current_price = float(df['Close'].iloc[-1])
        change = np.random.uniform(-0.02, 0.02)
        predicted_price = int(current_price * (1 + change))

        # 결과 반환
        result = {
            "stockName": name,
            "currentPrice": int(current_price),
            "predictedPrice": predicted_price,
            "confidence": 0.8 + np.random.uniform(-0.1, 0.1),
            "trend": "up" if predicted_price > current_price else "down",
            "historicalData": df.tail(20).reset_index().apply(
                lambda x: {
                    "date": x['Date'].strftime('%Y-%m-%d'),
                    "open": float(x['Open']),
                    "high": float(x['High']),
                    "low": float(x['Low']),
                    "close": float(x['Close'])
                }, axis=1
            ).tolist()
        }

        return jsonify(result)

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))