import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# 1. 페이지 설정 및 다크 테마 적용
st.set_page_config(page_title="바이낸스 5분봉 단타 대시보드", layout="wide")

# CSS: 블랙 배경 및 20pt 노란색 가격 스타일 적용
st.markdown("""
    <style>
    .main { background-color: #000000 !important; }
    .stApp { background-color: #000000 !important; }
    .price-text { font-size: 20pt; color: #FFFF00; font-weight: bold; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] > div { color: #FFFF00 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 - 설정 및 제어 (한글)
with st.sidebar:
    st.header("⚙️ 제어 패널")
    심볼 = st.text_input("거래 종목 (예: BTC/USDT)", value="BTC/USDT")
    
    st.divider()
    st.subheader("📊 RSI 상세 설정")
    RSI_기간 = st.slider("RSI 계산 기간", 2, 50, 14)
    스무스_기간 = st.slider("RSI 이동평균 기간", 2, 30, 9)
    과매수_기준 = st.slider("과매수 선", 50, 95, 70)
    과매도_기준 = st.slider("과매도 선", 5, 50, 30)
    
    st.divider()
    표시_캔들수 = st.slider("차트 표시 캔들 수", 50, 500, 200)
    실행_스위치 = st.checkbox("프로그램 시작", value=False)

# 3. 데이터 및 지표 계산 로직 (451 오류 해결을 위한 엔드포인트 수정)
@st.cache_data(ttl=5)
def 데이터_가져오기(symbol, rsi_p, smooth_p):
    try:
        # 지역 제한 오류 해결을 위한 선물 전용 API 주소(fapi) 설정
        exchange = ccxt.binance({
            'options': {'defaultType': 'future'},
            'urls': {
                'api': {
                    'public': 'https://fapi.binance.com/fapi/v1',
                    'private': 'https://fapi.binance.com/fapi/v1',
                }
            }
        })
        
        # 2400 이평선을 위해 3000개의 충분한 데이터 로드
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=3000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # EMA 계산 (흰색/적색/보라색/노란색 + 굵기 차이)
        df['EMA120'] = ta.ema(df['close'], length=120)
        df['EMA240'] = ta.ema(df['close'], length=240)
        df['EMA600'] = ta.ema(df['close'], length=600)
        df['EMA2400'] = ta.ema(df['close'], length=2400)

        # RSI 및 스무스선
        df['RSI'] = ta.rsi(df['close'], length=rsi_p)
        df['RSI_S'] = ta.ema(df['RSI'], length=smooth_p)
        
        return df
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return None

# 4. 메인 화면 렌더링
메인_영역 = st.empty()

if not 실행_스위치:
    st.info("사이드바에서 '프로그램 시작'을 체크해 주세요.")

while 실행_스위치:
    df = 데이터_가져오기(심볼, RSI_기간, 스무스_기간)
    
    if df is not None:
        # 차트 표시 범위 제한
        display_df = df.tail(표시_캔들수)
        현재가 = df['close'].iloc[-1]
        단기_이평 = df['EMA600'].iloc[-1]
        장기_이평 = df['EMA2400'].iloc[-1]
        
        with 메인_영역.container():
            # 상단: 노란색 20pt 현재가
            st.markdown(f'<p class="price-text">현재가: {현재가:,.2f} USDT</p>', unsafe_allow_html=True)
            
            # 메인 차트와 RSI를 하나의 Figure로 통합 (공유 X축)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # 1. 캔들스틱 및 EMA (1행)
            fig.add_trace(go.Candlestick(
                x=display_df['timestamp'], open=display_df['open'], high=display_df['high'], 
                low=display_df['low'], close=display_df['close'], name="5분봉"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA120'], line=dict(color='white', width=1), name='EMA 120'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA240'], line=dict(color='red', width=2), name='EMA 240'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA600'], line=dict(color='purple', width=3), name='EMA 600'), row=1, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['EMA2400'], line=dict(color='yellow', width=4), name='EMA 2400'), row=1, col=1)
            
            # 2. RSI 및 스무스선 (2행)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI'], line=dict(color='skyblue', width=1.5), name='RSI'), row=2, col=1)
            fig.add_trace(go.Scatter(x=display_df['timestamp'], y=display_df['RSI_S'], line=dict(color='yellow', width=1.5), name='RSI 스무스'), row=2, col=1)
            
            # RSI 기준선
            fig.add_hline(y=과매수_기준, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=과매도_기준, line_dash="dash", line_color="white", row=2, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)
            
            # 레이아웃 설정
            fig.update_layout(
                template="plotly_dark", 
                xaxis_rangeslider_visible=False, 
                height=700,
                margin=dict(t=30, b=10, l=10, r=10),
                paper_bgcolor='black',
                plot_bgcolor='black',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 5. 최하단 추세 표시 (글자색 로직 적용)
            st.divider()
            좌, 중, 우 = st.columns(3)
            
            # 단기 (보라색)
            if 현재가 > 단기_이평:
                좌.markdown(f'<h3 style="color:purple; text-align:center;">▲ 단기 상승 흐름</h3>', unsafe_allow_html=True)
            else:
                좌.markdown(f'<h3 style="color:#555555; text-align:center;">▼ 단기 하락 흐름</h3>', unsafe_allow_html=True)
                
            # 장기 (노란색)
            if 현재가 > 장기_이평:
                중.markdown(f'<h3 style="color:yellow; text-align:center;">★ 장기 대세 상승</h3>', unsafe_allow_html=True)
            else:
                중.markdown(f'<h3 style="color:#666600; text-align:center;">☆ 장기 대세 하락</h3>', unsafe_allow_html=True)
                
            # 이격도
            이격 = ((현재가 - 장기_이평) / 장기_이평) * 100
            우.metric("2400선 이격도", f"{이격:.2f}%")
            
        time.sleep(5)
