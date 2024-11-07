from flask import Flask, request, jsonify
from flask_cors import CORS
import FinanceDataReader as fdr
import numpy as np
from datetime import datetime, timedelta
import traceback
import os

app = Flask(__name__)
CORS(app)  # CORS 설정 추가

@app.route('/api/predict', methods=['POST'])
def predict_stock():
    try:
        data = request.get_json()
        query = data.get('stockCode')
        print(f"Received query: {query}")

        # 종목코드 찾기
        stock_code = query
        if not query.isdigit():
            # KRX 상장종목 전체 가져오기
            krx = fdr.StockListing('KRX')
            stock_info = krx[krx['Name'].str.contains(query, case=False, na=False)]
            if not stock_info.empty:
                stock_code = stock_info.iloc[0]['Code']
                stock_name = stock_info.iloc[0]['Name']
            else:
                return jsonify({'error': '종목을 찾을 수 없습니다.'}), 404
        else:
            krx = fdr.StockListing('KRX')
            stock_info = krx[krx['Code'] == query]
            if not stock_info.empty:
                stock_name = stock_info.iloc[0]['Name']
            else:
                return jsonify({'error': '종목을 찾을 수 없습니다.'}), 404

        # 주가 데이터 가져오기
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        df = fdr.DataReader(stock_code, start_date.strftime('%Y-%m-%d'))

        if df.empty:
            return jsonify({'error': '주가 데이터를 찾을 수 없습니다.'}), 404

        # 현재가
        current_price = float(df['Close'].iloc[-1])
        
        # 이동평균
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # 트렌드 판단
        trend = 'up' if df['MA5'].iloc[-1] > df['MA20'].iloc[-1] else 'down'
        
        # 변동성 계산
        volatility = df['Close'].pct_change().std()
        
        # 예측가격 계산 (±2% 범위 내)
        change = np.random.uniform(-0.02, 0.02)
        predicted_price = current_price * (1 + change)
        
        # 신뢰도 (60~90% 범위)
        confidence = 0.6 + (0.3 * (1 - abs(change)/0.02))

        result = {
            'stockName': stock_name,
            'currentPrice': int(current_price),
            'predictedPrice': int(predicted_price),
            'confidence': confidence,
            'trend': trend,
            'historicalData': [
                {
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close'])
                }
                for date, row in df.iterrows()
            ]
        }
        
        return jsonify(result)

    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)