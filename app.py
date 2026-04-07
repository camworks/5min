import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import time

# 1. 페이지 설정
st.set_page_config(page_title="코인 단타 대시보드", layout="wide")

# CSS: 블랙 배경 및 20pt 노란색 가격
st.markdown("""
    <style>
    .main { background-color: #000000 !important; }
    .stApp { background-color: #000000 !important; }
    .price-text { font-size: 20pt; color: #FFFF00; font-weight: bold; }
    div[data-testid="stMetricValue"] > div { color: #FFFF00 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 제어 패널
with st.sidebar:
    st.header("⚙️ 제어 패널")
    코인_심볼 = st.selectbox("종목 선택", ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"], index=0)
    
    st.divider()
    st.subheader("📊 RSI 설정")
    RSI_기간 = st.slider("RSI 기간", 2, 50, 14)
    스무스_기간 = st.slider("RSI 이동평균", 2, 30, 9)
    과매수 = st.slider("과매수(70)", 50, 95, 70)
    과매도 = st.slider("과매도(30)", 5, 50, 30)
    
    st.divider()
    실행 = st.checkbox("실시간 감시 시작", value=False)

# 3. 데이터 로직 (지역 제한 없는 소스 활용)
def 데이터_가져오기(symbol, rsi_p, smooth_p):
    try:
        # 5분봉 데이터를 2400선 계산이 가능할 만큼 충분히 가져옴 (최근 60일치)
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval="5m", period="60d")
        
        if df.empty: return None
        
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={'datetime': 'timestamp', 'date': 'timestamp'})

        # EMA 계산 (흰색 120 / 적색 240 / 보라색 600 / 노란색 2400)
        df['EMA120'] = ta.ema(df['close'], length=120)
        df['EMA240'] = ta.ema(df['close'], length=240)
        df['EMA600'] = ta.ema(df['close'], length=600)
        df['EMA2400'] = ta.ema(df['close'], length=2400)

        # RSI 및 스무스
        df['RSI'] = ta.rsi(df['close'], length=rsi_p)
        df['RSI_S'] = ta.ema(df['RSI'], length=smooth_p)
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

# 4. 화면 렌더링
메인 = st.empty()

if not 실행:
    st.info("사이드바에서 '실시간 감시 시작'을 체크하세요.")

while 실행:
    df = 데이터_가져오기(코인_심볼, RSI_기간, 스무스_기간)
    
    if df is not None:
        display_df = df.tail(150) # 차트에는 최근 150개만 표시
        현재가 = df['close'].iloc[-1]
        단기_이평 = df['EMA600'].iloc[-1]
        장기_이평 = df['EMA2400'].iloc[-1]
        
        with 메인.container():
            st.markdown(f'<p class="price-text">현재가: {현재가:,.2f} USD</p>', unsafe_allow_html=True)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # 메인 캔들 차트
            fig.add_trace(go.Candlestick(x=display_df['timestamp'], open=display_df['open'], 
                                        high=display_df['high'], low=display_df['low'], 
                                        close=display_df['close'], name="5분봉"), row=1, col=1)
            
            # EMA 라인 (요청하신 색상 및 굵기)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA120'], line=dict(color='white', width=1), name='120선'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA240'], line=dict(color='red', width=2), name='240선'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA600'], line=dict(color='purple', width=3), name='600선'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA2400'], line=dict(color='yellow', width=4), name='2400선'), row=1, col=1)
            
            # RSI 지표
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI'], line=dict(color='skyblue', width=1.5), name='RSI'), row=2, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI_S'], line=dict(color='yellow', width=1.5), name='RSI스무스'), row=2, col=1)
            fig.add_hline(y=과매수, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=과매도, line_dash="dash", line_color="white", row=2, col=1)
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=650,
                              paper_bgcolor='black', plot_bgcolor='black', margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
            
            # 하단 한글 추세 표시
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            if 현재가 > 단기_이평:
                c1.markdown('<h3 style="color:purple; text-align:center;">▲ 단기 상승 흐름</h3>', unsafe_allow_html=True)
            else:
                c1.markdown('<h3 style="color:#555555; text-align:center;">▼ 단기 하락 흐름</h3>', unsafe_allow_html=True)
                
            if 현재가 > 장기_이평:
                c2.markdown('<h3 style="color:yellow; text-align:center;">★ 장기 대세 상승</h3>', unsafe_allow_html=True)
            else:
                c2.markdown('<h3 style="color:#666600; text-align:center;">☆ 장기 대세 하락</h3>', unsafe_allow_html=True)
            
            이격 = ((현재가 - 장기_이평) / 장기_이평) * 100
            c3.metric("2400선 이격도", f"{이격:.2f}%")
            
    time.sleep(10) # 서버 부하 방지를 위해 10초 간격 업데이트
