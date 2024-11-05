const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 네이버 금융에서 주식 데이터 가져오기
async function getStockData(code) {
    try {
        // 네이버 금융 API URL
        const url = `https://polling.finance.naver.com/api/realtime/domestic/stock/${code}`;
        const response = await axios.get(url);
        
        if (response.data && response.data.datas && response.data.datas[0]) {
            return response.data.datas[0];
        }
        throw new Error('데이터를 찾을 수 없습니다.');
    } catch (error) {
        console.error('주식 데이터 조회 오류:', error);
        throw error;
    }
}

// 주가 예측 API 엔드포인트
app.post('/api/predict', async (req, res) => {
    try {
        const { stockCode } = req.body;
        const stockData = await getStockData(stockCode);
        
        // 현재가
        const currentPrice = parseInt(stockData.closePrice);
        const stockName = stockData.nm;
        
        // 전일 대비 등락률을 기반으로 예측
        const changeRate = parseFloat(stockData.fluctuationsRatio);
        
        // 다음날 예측 가격 (현재 추세를 기반으로 계산)
        let predictedChange = changeRate * (Math.random() * 0.5 + 0.75); // 변동폭 조절
        const predictedPrice = Math.round(currentPrice * (1 + predictedChange/100));
        
        // 전일 대비 등락률로 트렌드 결정
        const trend = changeRate > 0 ? 'up' : 'down';
        
        // 거래량 기반으로 신뢰도 계산
        const volume = parseInt(stockData.accTradeVolume);
        const avgVolume = parseInt(stockData.accTradeVolume5) / 5;
        const confidence = Math.min(0.9, Math.max(0.5, volume / avgVolume));

        res.json({
            currentPrice: currentPrice,
            predictedPrice: predictedPrice,
            confidence: confidence,
            trend: trend,
            stockName: stockName
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ 
            error: '예측 중 오류가 발생했습니다. 올바른 종목 코드인지 확인해주세요.' 
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});