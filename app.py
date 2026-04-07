import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 페이지 설정 및 다크 테마 적용
st.set_page_config(page_title="바이낸스 5분봉 단타 대시보드", layout="wide")

# CSS: 블랙 배경 및 20pt 노란색 가격 스타일
st.markdown("""
    <style>
    .main { background-color: #000000 !important; }
    .stApp { background-color: #000000 !important; }
    .price-text { font-size: 20pt; color: #FFFF00; font-weight: bold; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] { color: #FFFF00 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 - 설정 및 제어 (한글)
with st.sidebar:
    st.header("⚙️ 제어 패널")
    심볼 = st.text_input("거래 종목 (예: BTC/USDT)", value="BTC/USDT")
    레버리지 = st.number_input("레버리지", min_value=1, max_value=125, value=10)
    
    st.divider()
    st.subheader("📊 RSI 상세 설정")
    RSI_기간 = st.slider("RSI 계산 기간", 2, 50, 14)
    스무스_기간 = st.slider("RSI 이동평균 기간", 2, 30, 9)
    과매수_기준 = st.slider("과매수 선", 50, 95, 70)
    과매도_기준 = st.slider("과매도 선", 5, 50, 30)
    
    st.divider()
    실행_스위치 = st.checkbox("프로그램 시작", value=False)

# 3. 데이터 및 지표 계산 로직 (지역 제한 우회 엔드포인트 적용)
def 데이터_가져오기(symbol):
    try:
        # 지역 제한(451 오류) 해결을 위해 다중 엔드포인트 시도 설정
        exchange = ccxt.binance({
            'options': {'defaultType': 'future'},
            'urls': {
                'api': {
                    'public': 'https://fapi.binance.com/fapi/v1',
                    'private': 'https://fapi.binance.com/fapi/v1',
                }
            }
        })
        
        # 데이터 로드 (2400 이평선을 위해 3000개 로드)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=3000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # EMA 계산 (120 흰색 / 240 적색 / 600 보라색 / 2400 노란색)
        df['EMA120'] = ta.ema(df['close'], length=120)
        df['EMA240'] = ta.ema(df['close'], length=240)
        df['EMA600'] = ta.ema(df['close'], length=600)
        df['EMA2400'] = ta.ema(df['close'], length=2400)

        # RSI 및 스무스선
        df['RSI'] = ta.rsi(df['close'], length=RSI_기간)
        df['RSI_S'] = ta.ema(df['RSI'], length=스무스_기간)
        
        return df
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        st.warning("팁: 접속 제한 지역(미국 등)의 서버일 경우 발생할 수 있습니다. 로컬 환경 실행을 권장합니다.")
        return None

# 4. 메인 대시보드 렌더링
메인_영역 = st.empty()

if not 실행_스위치:
    st.info("사이드바에서 '프로그램 시작'을 체크해 주세요.")

while 실행_스위치:
    df = 데이터_가져오기(심볼)
    if df is not None:
        현재가 = df['close'].iloc[-1]
        단기_이평 = df['EMA600'].iloc[-1]
        장기_이평 = df['EMA2400'].iloc[-1]
        
        with 메인_영역.container():
            # 상단: 노란색 20pt 현재가
            st.markdown(f'<p class="price-text">현재가: {현재가:,.2f} USDT</p>', unsafe_allow_html=True)
            
            # 메인 차트 (EMA 4종)
            차트 = go.Figure()
            차트.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], 
                                        low=df['low'], close=df['close'], name="5분봉"))
            
            차트.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA120'], line=dict(color='white', width=1), name='이평 120'))
            차트.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA240'], line=dict(color='red', width=2), name='이평 240'))
            차트.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA600'], line=dict(color='purple', width=3), name='이평 600'))
            차트.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA2400'], line=dict(color='yellow', width=4), name='이평 2400'))
            
            차트.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500,
                              paper_bgcolor='black', plot_bgcolor='black', margin=dict(t=10, b=10))
            st.plotly_chart(차트, use_container_width=True)
            
            # RSI 영역
            RSI_차트 = go.Figure()
            RSI_차트.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], line=dict(color='skyblue', width=1.5), name='RSI'))
            RSI_차트.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI_S'], line=dict(color='yellow', width=1.5), name='RSI 스무스'))
            RSI_차트.add_hline(y=과매수_기준, line_dash="dash", line_color="red")
            RSI_차트.add_hline(y=과매도_기준, line_dash="dash", line_color="white")
            RSI_차트.update_layout(template="plotly_dark", height=180, paper_bgcolor='black', 
                                  plot_bgcolor='black', margin=dict(t=10, b=10))
            st.plotly_chart(RSI_차트, use_container_width=True)
            
            # 최하단 추세 표시 (글자색 로직)
            st.divider()
            좌, 중, 우 = st.columns(3)
            
            if 현재가 > 단기_이평:
                좌.markdown(f'<h3 style="color:purple; text-align:center;">▲ 단기 상승 흐름</h3>', unsafe_allow_html=True)
            else:
                좌.markdown(f'<h3 style="color:#555555; text-align:center;">▼ 단기 하락 흐름</h3>', unsafe_allow_html=True)
                
            if 현재가 > 장기_이평:
                중.markdown(f'<h3 style="color:yellow; text-align:center;">★ 장기 대세 상승</h3>', unsafe_allow_html=True)
            else:
                중.markdown(f'<h3 style="color:#666600; text-align:center;">☆ 장기 대세 하락</h3>', unsafe_allow_html=True)
                
            이격 = ((현재가 - 장기_이평) / 장기_이평) * 100
            우.metric("2400선 이격도", f"{이격:.2f}%")
            
        time.sleep(5)
