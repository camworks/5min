# streamlit_app.py 로 저장
import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 페이지 설정 (모바일 최적화)
st.set_page_config(layout="wide", page_title="Binance Monitor Mobile")

# 데이터 로직
@st.cache_data(ttl=5) # 5초마다 캐시 갱신
def fetch_binance_data(symbol, limit, rsi_period):
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=limit)
    df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    df['dt'] = pd.to_datetime(df['ts'], unit='ms') + timedelta(hours=9)
    
    # EMA 계산
    for p in [120, 240, 600, 2400]:
        df[f'ema{p}'] = df['close'].ewm(span=p, adjust=False).mean()
    
    # RSI 및 스무스 라인 (사용자 요청: 80)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    df['rsi_smooth'] = df['rsi'].rolling(window=rsi_period).mean()
    
    return df

# 상단 설정 바 (모바일에서는 메뉴박스로 표시됨)
st.title("?? Binance Real-time Monitor")
col1, col2, col3 = st.columns(3)
with col1:
    target_symbol = st.selectbox("코인", ["XRP/USDT", "BTC/USDT", "ETH/USDT"])
with col2:
    rsi_p = st.number_input("RSI 기간", value=80)
with col3:
    display_n = st.slider("표시 캔들 수", 50, 500, 200)

df = fetch_binance_data(target_symbol, 3000, rsi_p)

# Plotly 차트 생성 (터치 조작 가능)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# 1. 캔들차트 & EMA
fig.add_trace(go.Candlestick(x=df['dt'], open=df['open'], high=df['high'], 
                             low=df['low'], close=df['close'], name="Candle"), row=1, col=1)

colors = ['white', 'red', 'purple', 'yellow']
for p, c in zip([120, 240, 600, 2400], colors):
    fig.add_trace(go.Scatter(x=df['dt'], y=df[f'ema{p}'], line=dict(color=c, width=1), name=f"EMA{p}"), row=1, col=1)

# 2. RSI & Smooth
fig.add_trace(go.Scatter(x=df['dt'], y=df['rsi'], line=dict(color='white', width=1), name="RSI"), row=2, col=1)
fig.add_trace(go.Scatter(x=df['dt'], y=df['rsi_smooth'], line=dict(color='blue', width=1), name="Smooth"), row=2, col=1)

# 레이아웃 설정 (검정 배경 & 모바일 최적화)
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=800,
    margin=dict(l=10, r=10, t=10, bottom=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# 하단 정보
curr = df.iloc[-1]
st.metric("현재가", f"{curr['close']:,}", f"{curr['close'] - df.iloc[-2]['close']:.4f}")