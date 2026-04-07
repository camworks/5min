import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 페이지 및 테마 설정
st.set_page_config(page_title="바이낸스 5분봉 단타 대시보드", layout="wide")

# CSS를 이용한 블랙 배경 및 노란색 가격 스타일 강제 적용
st.markdown("""
    <style>
    .main { background-color: #000000 !important; }
    header, .stApp { background-color: #000000 !important; }
    .price-text { font-size: 24pt; color: #FFFF00; font-weight: bold; margin-bottom: 0px; }
    .status-box { padding: 10px; border-radius: 5px; background-color: #111111; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 - 사용자 제어 패널 (한글)
with st.sidebar:
    st.header("⚙️ 설정 및 제어")
    symbol = st.text_input("거래 종목 (선물)", value="BTC/USDT")
    leverage = st.number_input("레버리지 설정", min_value=1, max_value=125, value=10)
    
    st.divider()
    st.subheader("📊 RSI 지표 다이나믹 설정")
    rsi_period = st.slider("RSI 기간", 2, 50, 14)
    smooth_period = st.slider("RSI 이동평균 기간", 2, 30, 9)
    overbought = st.slider("과매수 기준선", 50, 95, 70)
    oversold = st.slider("과매도 기준선", 5, 50, 30)
    
    st.divider()
    run_program = st.checkbox("프로그램 시작", value=False)

# 3. 데이터 수집 및 지표 계산 함수
def fetch_and_process(symbol):
    try:
        # 바이낸스 선물 거래소 연결
        exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        # EMA 2400 계산을 위해 3000개의 충분한 데이터 로드
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=3000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # EMA 계산 (사용자 지정 색상 및 굵기 대응용)
        df['EMA120'] = ta.ema(df['close'], length=120)
        df['EMA240'] = ta.ema(df['close'], length=240)
        df['EMA600'] = ta.ema(df['close'], length=600)
        df['EMA2400'] = ta.ema(df['close'], length=2400)

        # RSI 및 스무스선 계산
        df['RSI'] = ta.rsi(df['close'], length=rsi_period)
        df['RSI_S'] = ta.ema(df['RSI'], length=smooth_period)
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

# 4. 메인 화면 렌더링 영역
placeholder = st.empty()

if not run_program:
    st.info("사이드바에서 '프로그램 시작'을 체크해주세요.")

while run_program:
    df = fetch_and_process(symbol)
    if df is not None:
        curr_price = df['close'].iloc[-1]
        ema600 = df['EMA600'].iloc[-1]
        ema2400 = df['EMA2400'].iloc[-1]
        
        with placeholder.container():
            # 상단: 20pt 이상 노란색 현재가 표시
            st.markdown(f'<p class="price-text">현재가: {curr_price:,.2f} USDT</p>', unsafe_allow_html=True)
            
            # 메인 캔들 차트 (EMA 4종 포함)
            fig = go.Figure()
            
            # 캔들스틱 (다크모드 고대비)
            fig.add_trace(go.Candlestick(
                x=df['timestamp'], open=df['open'], high=df['high'], 
                low=df['low'], close=df['close'], name="5분봉"
            ))
            
            # EMA 라인 (흰/적/보/노 및 굵기 적용)
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA120'], line=dict(color='white', width=1), name='EMA 120 (흰색)'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA240'], line=dict(color='red', width=2), name='EMA 240 (적색)'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA600'], line=dict(color='purple', width=3), name='EMA 600 (보라색)'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA2400'], line=dict(color='yellow', width=4), name='EMA 2400 (노란색)'))
            
            fig.update_layout(
                template="plotly_dark", 
                xaxis_rangeslider_visible=False, 
                height=550, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 하단: RSI 및 스무스선 영역
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], line=dict(color='skyblue', width=1.5), name='RSI 수치'))
            fig_rsi.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI_S'], line=dict(color='yellow', width=1.5), name='RSI 이동평균'))
            
            # RSI 기준선 (한글 설정값 반영)
            fig_rsi.add_hline(y=overbought, line_dash="dash", line_color="red")
            fig_rsi.add_hline(y=oversold, line_dash="dash", line_color="white")
            
            fig_rsi.update_layout(
                template="plotly_dark", 
                height=200, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=10, b=10)
            )
            st.plotly_chart(fig_rsi, use_container_width=True)
            
            # 최하단: 추세 상태 표시 (글자색 로직 적용)
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            # 단기 추세 (보라색)
            if curr_price > ema600:
                c1.markdown(f'<h3 style="color:purple; text-align:center;">▲ 단기 상승 흐름</h3>', unsafe_allow_html=True)
            else:
                c1.markdown(f'<h3 style="color:#555555; text-align:center;">▼ 단기 하락 흐름</h3>', unsafe_allow_html=True)
                
            # 장기 추세 (노란색)
            if curr_price > ema2400:
                c2.markdown(f'<h3 style="color:yellow; text-align:center;">★ 장기 대세 상승</h3>', unsafe_allow_html=True)
            else:
                c2.markdown(f'<h3 style="color:#666600; text-align:center;">☆ 장기 대세 하락</h3>', unsafe_allow_html=True)
                
            # 이격도 표시
            disparity = ((curr_price - ema2400) / ema2400) * 100
            c3.metric("이격도 (2400선 기준)", f"{disparity:.2f}%")
            
        time.sleep(5) # 5초마다 데이터 갱신
