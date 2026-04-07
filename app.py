import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    코인_심볼 = st.selectbox("종목 선택", ["BTC-USD", "ETH-USD", "SOL-USD"], index=0)
    
    st.divider()
    st.subheader("📊 RSI 설정")
    RSI_기간 = st.slider("RSI 기간", 2, 50, 14)
    스무스_기간 = st.slider("RSI 이동평균", 2, 30, 9)
    
    st.divider()
    실행 = st.checkbox("실시간 감시 시작", value=False)

# 3. 보조지표 직접 계산 함수 (pandas-ta 설치 오류 회피용)
def calculate_indicators(df, rsi_p, smooth_p):
    # EMA 계산
    df['EMA120'] = df['close'].ewm(span=120, adjust=False).mean()
    df['EMA240'] = df['close'].ewm(span=240, adjust=False).mean()
    df['EMA600'] = df['close'].ewm(span=600, adjust=False).mean()
    df['EMA2400'] = df['close'].ewm(span=2400, adjust=False).mean()
    
    # RSI 계산
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI_S'] = df['RSI'].ewm(span=smooth_p, adjust=False).mean()
    return df

# 4. 데이터 로직
def get_data(symbol):
    try:
        # 5분봉 데이터를 2400선 계산을 위해 충분히 가져옴
        df = yf.download(tickers=symbol, period="60d", interval="5m", progress=False)
        if df.empty: return None
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

# 5. 화면 렌더링
메인 = st.empty()

if not 실행:
    st.info("사이드바에서 '실시간 감시 시작'을 체크하세요.")

while 실행:
    raw_df = get_data(코인_심볼)
    if raw_df is not None:
        df = calculate_indicators(raw_df, RSI_기간, 스무스_기간)
        display_df = df.tail(150)
        현재가 = df['close'].iloc[-1]
        단기_이평 = df['EMA600'].iloc[-1]
        장기_이평 = df['EMA2400'].iloc[-1]
        
        with 메인.container():
            st.markdown(f'<p class="price-text">현재가: {현재가:,.2f} USD</p>', unsafe_allow_html=True)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # 메인 차트 및 EMA (흰120, 적240, 보600, 노2400)
            fig.add_trace(go.Candlestick(x=display_df['timestamp'], open=display_df['open'], 
                                        high=display_df['high'], low=display_df['low'], 
                                        close=display_df['close'], name="5분봉"), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA120'], line=dict(color='white', width=1), name='120'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA240'], line=dict(color='red', width=2), name='240'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA600'], line=dict(color='purple', width=3), name='600'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA2400'], line=dict(color='yellow', width=4), name='2400'), row=1, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI'], line=dict(color='skyblue', width=1.5), name='RSI'), row=2, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI_S'], line=dict(color='yellow', width=1.5), name='스무스'), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600,
                              paper_bgcolor='black', plot_bgcolor='black', margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
            
            # 하단 추세 표시
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
            
    time.sleep(10)
