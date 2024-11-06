from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import FinanceDataReader as fdr
import numpy as np
from datetime import datetime, timedelta
import traceback
import os

app = Flask(__name__, static_folder='public')
CORS(app, resources={
    r"/*": {
        "origins": ["https://stock-predictor-weld.vercel.app", 
                   "http://localhost:3000"],
        "methods": ["OPTIONS", "GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Static files
@app.route('/')
def serve():
    return "Stock Predictor API is running!"

def get_stock_code(query):
    """종목명 또는 종목코드로 종목코드를 찾는 함수"""
    try:
        # KRX 상장종목 전체 가져오기
        krx = fdr.StockListing('KRX')
        
        # 입력값이 숫자인 경우 (종목코드)
        if query.isdigit():
            stock_info = krx[krx['Code'] == query]
            if not stock_info.empty:
                return query, stock_info['Name'].iloc[0]
        
        # 입력값이 한글인 경우 (종목명)
        else:
            stock_info = krx[krx['Name'].str.contains(query, case=False, na=False)]
            if not stock_info.empty:
                return stock_info['Code'].iloc[0], stock_info['Name'].iloc[0]
        
        return None, None
    except Exception as e:
        print(f"Error in get_stock_code: {str(e)}")
        return None, None

def calculate_predicted_price(current_price, trend, volatility):
    # 변동성을 1%~3% 범위로 제한
    max_change = min(0.03, volatility)
    min_change = max_change / 3
    
    if trend == 'up':
        # 상승 추세: 0.3% ~ 3% 상승
        change_rate = np.random.uniform(min_change, max_change)
    else:
        # 하락 추세: -0.3% ~ -3% 하락
        change_rate = np.random.uniform(-max_change, -min_change)
    
    # 예측 가격 계산
    predicted_price = current_price * (1 + change_rate)
    
    # 신뢰도 계산 개선
    confidence = 0.7 + (0.2 * (1 - abs(change_rate)/max_change))
    
    return predicted_price, confidence, change_rate

@app.route('/api/predict', methods=['POST', 'OPTIONS'])
def predict_stock():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        query = request.json.get('stockCode')
        print(f"Received query: {query}")

        # 종목코드 찾기
        stock_code, stock_name = get_stock_code(query)
        
        if not stock_code:
            return jsonify({'error': f'"{query}" 에 해당하는 종목을 찾을 수 없습니다.'}), 404

        print(f"Found stock: {stock_name} ({stock_code})")

        try:
            # 현재 날짜와 60일 전 날짜 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            # 종목 코드를 이용해 데이터 가져오기
            df = fdr.DataReader(stock_code, start_date.strftime('%Y-%m-%d'))
            print(f"Successfully fetched data for {stock_name}")

            if df.empty:
                raise ValueError('데이터가 없습니다')

            # 최근 종가
            current_price = float(df['Close'].iloc[-1])
            
            # 이동평균 계산
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()

            # 변동성 계산
            daily_returns = df['Close'].pct_change()
            volatility = daily_returns.std()

            # 트렌드 결정
            ma5 = df['MA5'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]
            trend = 'up' if ma5 > ma20 else 'down'

            # 예측 가격 계산
            predicted_price, confidence, change_rate = calculate_predicted_price(current_price, trend, volatility)

            # 변동률 계산 (소수점 2자리까지)
            change_percentage = round(change_rate * 100, 2)

            # 결과 데이터 구성
            result = {
                'currentPrice': int(current_price),
                'predictedPrice': int(predicted_price),
                'confidence': float(confidence),
                'trend': trend,
                'stockName': stock_name,
                'changeRate': change_percentage,
                'historicalData': [
                    {
                        'date': date.strftime('%Y-%m-%d'),
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close'])
                    }
                    for date, row in df.tail(20).iterrows()  # 최근 20일간의 데이터
                ]
            }

            print(f"Returning result: {result}")
            return jsonify(result)

        except Exception as e:
            print(f"Data fetch error: {str(e)}")
            raise

    except Exception as e:
        error_msg = f"예측 중 오류가 발생했습니다: {str(e)}"
        print(f"Error: {error_msg}")
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)