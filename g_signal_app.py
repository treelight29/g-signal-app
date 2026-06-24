"""
G-SIGNAL v0.1 — 스윙 매수 적합도 앱
=====================================
신호 엔진: G_US_F1 (가격구조 + 거래량 + 금리충격 필터)
검증 기반: Phase 1~3B 통과 (MDD -23.5%, 2022 방어 확인)

앱 목적:
  종목 입력 → 20거래일 스윙 관점 매수/홀딩/매도 점수 출력
  ※ 이 점수는 "확률"이 아니라 백테스트 기반 기술적 적합도 점수입니다.

실행: py -m streamlit run g_signal_app.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="G-SIGNAL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #0a0e17;
    color: #e2e8f0;
}

/* 전체 배경 */
.stApp { background-color: #0a0e17; }
.block-container { padding: 1.5rem 2rem; max-width: 1200px; }

/* 사이드바 */
section[data-testid="stSidebar"] {
    background-color: #0f1623;
    border-right: 1px solid #1e2a3a;
}

/* 점수 카드 */
.score-wrap {
    display: flex;
    gap: 12px;
    margin: 1rem 0;
}
.score-card {
    flex: 1;
    padding: 1.4rem 1rem;
    border-radius: 10px;
    text-align: center;
    border: 1px solid #1e2a3a;
    position: relative;
    overflow: hidden;
}
.score-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.card-buy   { background: #0a1a0f; }
.card-buy::before   { background: #22c55e; }
.card-hold  { background: #1a1500; }
.card-hold::before  { background: #eab308; }
.card-sell  { background: #1a0a0a; }
.card-sell::before  { background: #ef4444; }

.score-label { font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: #64748b; margin-bottom: 6px; }
.score-num-buy  { font-family: 'Space Mono', monospace; font-size: 2.6rem; font-weight: 700; color: #22c55e; line-height: 1; }
.score-num-hold { font-family: 'Space Mono', monospace; font-size: 2.6rem; font-weight: 700; color: #eab308; line-height: 1; }
.score-num-sell { font-family: 'Space Mono', monospace; font-size: 2.6rem; font-weight: 700; color: #ef4444; line-height: 1; }
.score-sub  { font-size: 0.75rem; color: #475569; margin-top: 4px; }

/* 판정 배너 */
.verdict-banner {
    padding: 0.9rem 1.2rem;
    border-radius: 8px;
    margin: 0.8rem 0 1.2rem;
    font-size: 0.95rem;
    font-weight: 500;
    border-left: 4px solid;
}
.verdict-buy  { background: #0f2d1a; border-color: #22c55e; color: #86efac; }
.verdict-hold { background: #2d2500; border-color: #eab308; color: #fde047; }
.verdict-sell { background: #2d0f0f; border-color: #ef4444; color: #fca5a5; }
.verdict-filter { background: #1a1a2d; border-color: #6366f1; color: #a5b4fc; }

/* 지표 행 */
.ind-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid #1e2a3a;
    font-size: 0.88rem;
}
.ind-name { color: #94a3b8; }
.ind-val  { font-family: 'Space Mono', monospace; font-size: 0.82rem; color: #64748b; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
.b-pos  { background: #14532d; color: #86efac; }
.b-neg  { background: #7f1d1d; color: #fca5a5; }
.b-neu  { background: #1c1917; color: #a8a29e; }
.b-warn { background: #78350f; color: #fcd34d; }

/* 섹션 헤더 */
.sec-hdr {
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #3b82f6;
    margin: 1.4rem 0 0.5rem;
    font-weight: 600;
}

/* 손절선 박스 */
.sl-box {
    background: #0f1623;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
}

/* 면책 고지 */
.disclaimer {
    margin-top: 1.5rem;
    padding: 0.8rem 1rem;
    background: #0f1623;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    font-size: 0.72rem;
    color: #475569;
    line-height: 1.6;
}

/* F1 필터 상태 */
.f1-box {
    padding: 0.7rem 1rem;
    border-radius: 6px;
    font-size: 0.85rem;
    margin: 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.f1-ok   { background: #0f2d1a; color: #86efac; border: 1px solid #166534; }
.f1-warn { background: #2d1a00; color: #fcd34d; border: 1px solid #92400e; }

/* Streamlit 위젯 스타일 */
.stTextInput > div > div > input {
    background: #0f1623 !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 6px !important;
    font-family: 'Space Mono', monospace !important;
}
div[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace;
    color: #e2e8f0;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# 종목명 → 티커 변환 (Claude API 활용)
# ══════════════════════════════════════════════════════════
def resolve_ticker(query: str) -> tuple[str, str]:
    """
    입력값이 티커이면 그대로 반환.
    종목명처럼 보이면 Claude API로 티커 추출.
    반환: (ticker, company_name)
    """
    query = query.strip()

    # 티커로 보이면 바로 반환
    # 조건: 영문+숫자 1~6자, 또는 .KS/.KQ/.T 등 접미사 포함
    import re
    if re.match(r'^[A-Z0-9\.\-\^]{1,10}$', query.upper()):
        return query.upper(), query.upper()

    # 종목명 → Claude API로 티커 추출
    try:
        import json, requests
        prompt = f"""다음 종목명에 해당하는 Yahoo Finance 티커 심볼을 알려주세요.

종목명: {query}

규칙:
- 미국 상장 주식은 그냥 티커 (예: AAPL, NVDA, TSLA)
- 한국 주식은 숫자6자리.KS 형식 (예: 005930.KS)
- 반드시 JSON 형식으로만 답하세요: {{"ticker": "AAPL", "name": "Apple Inc."}}
- 모르면: {{"ticker": "UNKNOWN", "name": "알 수 없음"}}
- JSON 외 다른 텍스트 절대 금지"""

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=10
        )
        data = response.json()
        text = data['content'][0]['text'].strip()

        # JSON 파싱
        text = text.replace('```json','').replace('```','').strip()
        result = json.loads(text)
        ticker = result.get('ticker', 'UNKNOWN')
        name   = result.get('name', query)

        if ticker == 'UNKNOWN':
            return query.upper(), query

        return ticker, name

    except Exception:
        # API 실패 시 입력값 그대로 사용
        return query.upper(), query


# ══════════════════════════════════════════════════════════
# 데이터 수집
# ══════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch(ticker: str, days=400) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[['Open','High','Low','Close','Volume']].dropna()

@st.cache_data(ttl=300)
def fetch_tnx() -> pd.Series:
    df = yf.download('^TNX', period='6mo', progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df['Close'].dropna()


# ══════════════════════════════════════════════════════════
# 지표 계산
# ══════════════════════════════════════════════════════════
def compute(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d['Close']

    for n in [20, 60, 200]:
        d[f'sma{n}'] = c.rolling(n).mean()

    # RSI (참고용)
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    d['rsi'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    # MACD (참고용)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    d['macd']     = ema12 - ema26
    d['macd_sig'] = d['macd'].ewm(span=9, adjust=False).mean()
    d['macd_hist']= d['macd'] - d['macd_sig']

    # 볼린저밴드
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    d['bb_upper'] = bb_mid + 2*bb_std
    d['bb_lower'] = bb_mid - 2*bb_std
    d['bb_mid']   = bb_mid
    d['bb_width'] = (d['bb_upper'] - d['bb_lower']) / bb_mid
    d['bbw_pct20']= d['bb_width'].rolling(20).rank(pct=True)

    # ATR
    hl = d['High'] - d['Low']
    hc = (d['High'] - c.shift(1)).abs()
    lc = (d['Low']  - c.shift(1)).abs()
    d['atr'] = pd.concat([hl,hc,lc], axis=1).max(axis=1).rolling(14).mean()

    # 거래량
    d['vol_ma20']  = d['Volume'].rolling(20).mean()
    d['vol_ratio'] = d['Volume'] / d['vol_ma20']
    d['is_up']     = (c >= d['Open']).astype(int)

    # G 신호 피처
    rl = c.rolling(20).min()
    rh = c.rolling(20).max()
    d['price_pos20']   = (c - rl) / (rh - rl).replace(0, np.nan)
    low10 = c.rolling(10).min().shift(1)
    d['low_rebound10'] = (c - low10) / low10.replace(0, np.nan)
    vol5 = d['Volume'].rolling(5).mean().shift(1)
    d['vol_squeeze']   = (vol5 < d['vol_ma20']*0.7) & (d['Volume'] > d['Volume'].shift(1))

    return d


# ══════════════════════════════════════════════════════════
# G 신호 점수 계산
# ══════════════════════════════════════════════════════════
def g_score(row) -> tuple[float, list]:
    """G 신호 원점수 + 상세 근거 반환"""
    s = 0.0
    detail = []

    # 가격 위치 (박스권 내)
    pp = row['price_pos20']
    if pp < 0.2:
        s += 30; detail.append(('가격 박스 하단 (강한 눌림목)', +30, 'pos'))
    elif pp < 0.4:
        s += 20; detail.append(('가격 박스 하단부', +20, 'pos'))
    elif pp < 0.6:
        s += 10; detail.append(('가격 박스 중간', +10, 'neu'))
    elif pp > 0.8:
        s -= 15; detail.append(('가격 박스 상단 (추격 위험)', -15, 'neg'))
    else:
        detail.append(('가격 박스 중상단', 0, 'neu'))

    # 신저가 대비 반등
    lr = row['low_rebound10']
    if lr > 0.05:
        s += 25; detail.append(('10일 저점 대비 +5% 이상 반등', +25, 'pos'))
    elif lr > 0.02:
        s += 15; detail.append(('10일 저점 대비 반등 중', +15, 'pos'))
    elif lr > 0:
        s +=  5; detail.append(('10일 저점 대비 소폭 반등', +5, 'neu'))
    else:
        s -= 10; detail.append(('10일 저점 이탈 또는 저점 형성 중', -10, 'neg'))

    # 거래량 스퀴즈 (에너지 축적)
    if row['vol_squeeze']:
        s += 25; detail.append(('거래량 스퀴즈 후 증가 (에너지 축적)', +25, 'pos'))
    else:
        detail.append(('거래량 스퀴즈 없음', 0, 'neu'))

    # 거래량 + 방향
    vr = row['vol_ratio']
    if vr > 1.3 and row['is_up']:
        s += 20; detail.append((f'거래량 {vr:.1f}배 + 양봉', +20, 'pos'))
    elif vr > 1.3 and not row['is_up']:
        s -= 20; detail.append((f'거래량 {vr:.1f}배 + 음봉 (매도 압력)', -20, 'neg'))
    elif vr < 0.5:
        s -= 15; detail.append((f'거래량 급감 ({vr:.1f}배)', -15, 'neg'))
    else:
        detail.append((f'거래량 보통 ({vr:.1f}배)', 0, 'neu'))

    # SMA 위치
    if row['Close'] > row['sma20']:
        s += 10; detail.append(('종가 > SMA20', +10, 'pos'))
    else:
        detail.append(('종가 < SMA20', 0, 'neg'))

    if row['Close'] > row['sma60']:
        s +=  5; detail.append(('종가 > SMA60', +5, 'pos'))
    else:
        detail.append(('종가 < SMA60', 0, 'neg'))

    return s, detail


def calc_scores(g_raw: float, f1_ok: bool,
                avg_price: float, close: float, atr: float) -> dict:
    """
    G 원점수 → 매수/홀딩/매도 % 변환
    v1b 전략 기반: Top10, -8% 손절, 20거래일 보유
    """
    # F1 필터 ON이면 매수 금지
    if not f1_ok:
        return {'buy': 5, 'hold': 20, 'sell': 75,
                'verdict': 'filter',
                'verdict_text': '금리충격 필터 ON — 신규 매수 신호 비활성화 구간'}

    # G 점수 정규화 (이론 범위: -65 ~ +110)
    g_norm = (g_raw + 65) / 175  # 0~1로 정규화
    g_norm = max(0.0, min(1.0, g_norm))

    # 기본 매수 점수
    buy_raw = g_norm * 100

    # 보유 종목 손절 위험 반영
    sell_extra = 0
    if avg_price and avg_price > 0:
        pnl = (close - avg_price) / avg_price
        if pnl <= -0.08:
            sell_extra = 60   # 손절 트리거
        elif pnl <= -0.05:
            sell_extra = 30   # 손절 주의
        elif pnl >= 0.15:
            sell_extra = 20   # 익절 고려

    # 최종 점수 산출
    buy_score  = max(0, buy_raw - sell_extra * 0.5)
    sell_score = max(0, (100 - buy_raw) * 0.6 + sell_extra * 0.4)
    hold_score = max(0, 100 - buy_score - sell_score)

    # 정규화
    total = buy_score + hold_score + sell_score
    if total == 0: total = 1
    buy_pct  = round(buy_score  / total * 100)
    hold_pct = round(hold_score / total * 100)
    sell_pct = round(100 - buy_pct - hold_pct)

    # 판정
    if buy_pct >= 50:
        verdict = 'buy'
        verdict_text = '매수 적합 — G 신호 상위권, 20거래일 스윙 진입 고려 가능'
    elif sell_pct >= 50:
        verdict = 'sell'
        verdict_text = '매도/관망 — G 신호 하위권, 신규 진입 보류'
    else:
        verdict = 'hold'
        verdict_text = '홀딩/관망 — 명확한 신호 없음, 기존 보유자는 유지'

    return {'buy': buy_pct, 'hold': hold_pct, 'sell': sell_pct,
            'verdict': verdict, 'verdict_text': verdict_text}



# ══════════════════════════════════════════════════════════
# 스캐너 종목 리스트
# ══════════════════════════════════════════════════════════
SCAN_US = {
    'AAPL':'Apple', 'MSFT':'Microsoft', 'NVDA':'NVIDIA', 'GOOGL':'Alphabet',
    'META':'Meta', 'AMZN':'Amazon', 'JPM':'JPMorgan', 'BAC':'BofA',
    'GS':'Goldman', 'WFC':'Wells Fargo', 'JNJ':'J&J', 'UNH':'UnitedHealth',
    'PFE':'Pfizer', 'ABT':'Abbott', 'XOM':'ExxonMobil', 'CVX':'Chevron',
    'WMT':'Walmart', 'HD':'Home Depot', 'MCD':"McDonald's", 'NKE':'Nike',
    'CAT':'Caterpillar', 'HON':'Honeywell', 'UPS':'UPS', 'NEE':'NextEra',
    'AMT':'AmericanTower', 'LIN':'Linde', 'APD':'AirProducts',
    'VZ':'Verizon', 'T':'AT&T', 'DIS':'Disney',
}

SCAN_KR = {
    '005930.KS':'삼성전자', '000660.KS':'SK하이닉스', '035420.KS':'NAVER',
    '005380.KS':'현대차', '051910.KS':'LG화학', '006400.KS':'삼성SDI',
    '035720.KS':'카카오', '003550.KS':'LG', '012330.KS':'현대모비스',
    '066570.KS':'LG전자', '032830.KS':'삼성생명', '017670.KS':'SK텔레콤',
    '030200.KS':'KT', '096770.KS':'SK이노베이션', '009150.KS':'삼성전기',
    '034730.KS':'SK', '011200.KS':'HMM', '010130.KS':'고려아연',
    '028260.KS':'삼성물산', '018260.KS':'삼성SDS',
}


@st.cache_data(ttl=600)
def scan_market(market: str) -> pd.DataFrame:
    """전체 종목 스캔 — 매수 적합도 계산"""
    tickers = SCAN_US if market == 'US' else SCAN_KR
    f1_ok, _ = check_f1()

    rows = []
    for ticker, name in tickers.items():
        try:
            df = fetch(ticker, days=300)
            if len(df) < 130:
                continue
            d   = compute(df)
            row = d.iloc[-1]
            if pd.isna(row['price_pos20']) or pd.isna(row['bbw_pct20']):
                continue
            close = float(row['Close'])
            atr   = float(row['atr']) if not pd.isna(row['atr']) else 0
            g_raw, _ = g_score(row)
            sc = calc_scores(g_raw, f1_ok, None, close, atr)
            rows.append({
                'ticker':   ticker,
                'name':     name,
                'close':    close,
                'buy_pct':  sc['buy'],
                'hold_pct': sc['hold'],
                'sell_pct': sc['sell'],
                'g_raw':    round(g_raw, 1),
                'rsi':      round(row['rsi'], 1) if not pd.isna(row['rsi']) else None,
                'vol_ratio':round(row['vol_ratio'], 2) if not pd.isna(row['vol_ratio']) else None,
                'verdict':  sc['verdict'],
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    df_result = pd.DataFrame(rows).sort_values('buy_pct', ascending=False).reset_index(drop=True)
    return df_result

# ══════════════════════════════════════════════════════════
# F1 금리충격 필터
# ══════════════════════════════════════════════════════════
def check_f1() -> tuple[bool, float]:
    """F1 필터: 10년물 금리 60일 변화폭 > +0.75%p이면 매수 금지"""
    try:
        tnx = fetch_tnx()
        if len(tnx) < 62:
            return True, float('nan')
        change60 = tnx.iloc[-1] - tnx.iloc[-61]
        return change60 <= 0.75, change60
    except:
        return True, float('nan')


# ══════════════════════════════════════════════════════════
# 차트
# ══════════════════════════════════════════════════════════
def make_chart(df: pd.DataFrame, ticker: str,
               avg_price: float = None, atr: float = None) -> go.Figure:
    d = compute(df).tail(120)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.03,
    )

    # 캔들
    fig.add_trace(go.Candlestick(
        x=d.index, open=d['Open'], high=d['High'],
        low=d['Low'], close=d['Close'], name=ticker,
        increasing_line_color='#22c55e', decreasing_line_color='#ef4444',
        increasing_fillcolor='rgba(34,197,94,0.8)',
        decreasing_fillcolor='rgba(239,68,68,0.8)',
    ), row=1, col=1)

    # SMA
    for col_, color_, w_ in [('sma20','#3b82f6',1.5),('sma60','#eab308',1.2),('sma200','#8b5cf6',1.0)]:
        fig.add_trace(go.Scatter(x=d.index, y=d[col_], name=col_.upper(),
                                  line=dict(color=color_, width=w_), opacity=0.8), row=1, col=1)

    # 볼린저밴드
    fig.add_trace(go.Scatter(x=d.index, y=d['bb_upper'], name='BB Upper',
                              line=dict(color='#475569', width=0.8, dash='dot'), opacity=0.4), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['bb_lower'], name='BB Lower',
                              line=dict(color='#475569', width=0.8, dash='dot'), opacity=0.4,
                              fill='tonexty', fillcolor='rgba(71,85,105,0.05)'), row=1, col=1)

    # 평균 매수가 + 손절선
    if avg_price and avg_price > 0 and atr:
        sl = avg_price * 0.92   # -8%
        fig.add_hline(y=avg_price, line_color='#22c55e', line_width=1.2,
                       line_dash='dash', annotation_text=f'매수가 {avg_price:.2f}',
                       annotation_font_color='#22c55e', row=1, col=1)
        fig.add_hline(y=sl, line_color='#ef4444', line_width=1.2,
                       line_dash='dash', annotation_text=f'손절 {sl:.2f} (-8%)',
                       annotation_font_color='#ef4444', row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=d.index, y=d['rsi'], name='RSI',
                              line=dict(color='#3b82f6', width=1.5)), row=2, col=1)
    for lvl, c_ in [(70,'#ef4444'),(50,'#475569'),(30,'#22c55e')]:
        fig.add_hline(y=lvl, line_dash='dot', line_color=c_, opacity=0.35, row=2, col=1)

    # MACD
    colors = ['#22c55e' if v >= 0 else '#ef4444' for v in d['macd_hist']]
    fig.add_trace(go.Bar(x=d.index, y=d['macd_hist'], name='Hist',
                          marker_color=colors, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['macd'],     name='MACD',
                              line=dict(color='#3b82f6', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['macd_sig'], name='Signal',
                              line=dict(color='#eab308', width=1.2)), row=3, col=1)

    fig.update_layout(
        paper_bgcolor='#0a0e17', plot_bgcolor='#0f1623',
        font=dict(color='#94a3b8', size=11),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation='h', y=1.02, bgcolor='rgba(0,0,0,0)', font_size=10),
        height=580, margin=dict(l=10,r=10,t=20,b=10)
    )
    fig.update_xaxes(gridcolor='#1e2a3a', showgrid=True)
    fig.update_yaxes(gridcolor='#1e2a3a', showgrid=True)
    return fig


# ══════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════
def sidebar():
    with st.sidebar:
        st.markdown("## 📡 G-SIGNAL")
        st.markdown("<div style='font-size:0.78rem;color:#475569;margin-bottom:1rem'>스윙 매수 적합도 분석 v0.1</div>", unsafe_allow_html=True)
        st.divider()

        query = st.text_input(
            "종목명 또는 티커",
            value="AAPL",
            help="종목명: 삼성전자, 애플, NVIDIA / 티커: AAPL, 005930.KS"
        ).strip()

        # 종목명 → 티커 변환
        ticker, resolved_name = resolve_ticker(query)

        # 변환 결과 표시
        if query and query.upper() != ticker and ticker != 'UNKNOWN':
            st.markdown(
                f"<div style='font-size:0.78rem;color:#22c55e;margin-top:4px'>"
                f"✓ {resolved_name} → <b>{ticker}</b></div>",
                unsafe_allow_html=True
            )
        elif ticker == 'UNKNOWN':
            st.markdown(
                "<div style='font-size:0.78rem;color:#ef4444;margin-top:4px'>"
                "⚠ 종목을 찾지 못했습니다. 티커를 직접 입력해주세요.</div>",
                unsafe_allow_html=True
            )

        st.divider()
        st.markdown("<div style='font-size:0.8rem;color:#64748b;margin-bottom:8px'>보유 종목 옵션</div>", unsafe_allow_html=True)
        has_pos = st.toggle("보유 중인 종목", value=False)
        avg_price = None
        if has_pos:
            avg_price = st.number_input("평균 매수가", min_value=0.01, value=100.0, step=0.01)

        st.divider()
        run = st.button("분석 실행", use_container_width=True, type="primary")

        st.markdown("""
        <div style='font-size:0.72rem;color:#334155;margin-top:1.5rem;line-height:1.7'>
        <b>신호 엔진 정보</b><br>
        · G_US_F1 (Phase 1~3B 검증)<br>
        · MDD -23.5% (SPY -33.7%)<br>
        · 20거래일 스윙 기준<br>
        · -8% 손절 내장<br>
        · 금리충격 필터 연동
        </div>
        """, unsafe_allow_html=True)

    return ticker, resolved_name, has_pos, avg_price, run


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════
def badge(text, kind):
    cls = {'pos':'b-pos','neg':'b-neg','neu':'b-neu','warn':'b-warn'}.get(kind,'b-neu')
    return f'<span class="badge {cls}">{text}</span>'

def ind_row(name, val_str, badge_text, badge_kind):
    return f"""
    <div class="ind-row">
        <span class="ind-name">{name}</span>
        <span><span class="ind-val">{val_str}&nbsp;</span>{badge(badge_text, badge_kind)}</span>
    </div>"""

def main():
    ticker, resolved_name, has_pos, avg_price, run = sidebar()

    st.markdown("# 📡 G-SIGNAL")
    st.markdown("<div style='color:#475569;font-size:0.9rem;margin-bottom:1.5rem'>20거래일 스윙 매수 적합도 분석 — G_US_F1 신호 엔진 v0.1</div>", unsafe_allow_html=True)

    if not run:
        st.markdown("""
<div style="background:#0f1623;border:1px solid #1e2a3a;border-radius:12px;padding:1.8rem 2rem;margin-bottom:1.5rem">

<div style="font-size:0.68rem;letter-spacing:0.14em;text-transform:uppercase;color:#3b82f6;font-weight:600;margin-bottom:1rem">전략 개요</div>

<div style="display:flex;gap:2rem;flex-wrap:wrap">

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">📋 개발 과정</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<b style="color:#e2e8f0">Phase 1</b> — 5개 전략 후보 신호 품질 검증<br>
<b style="color:#e2e8f0">Phase 1.5</b> — G 전략 실패 원인 진단<br>
<b style="color:#e2e8f0">Phase 2A</b> — SMA200 필터 테스트 → 실패<br>
<b style="color:#e2e8f0">Phase 2B</b> — 금리충격 필터(F1) 테스트 → 통과<br>
<b style="color:#e2e8f0">Phase 3B</b> — 포트폴리오 백테스트 → v1b 확정
</div>
</div>

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">⚙️ 전략 핵심 규칙</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<b style="color:#e2e8f0">신호</b> — 가격구조 + 거래량 (후행지표 최소화)<br>
<b style="color:#e2e8f0">필터</b> — 10년물 금리 60일 변화 ＞ +0.75%p 시 매수 중단<br>
<b style="color:#e2e8f0">손절</b> — 진입가 대비 -8% 고정<br>
<b style="color:#e2e8f0">보유</b> — 20거래일 스윙 기준<br>
<b style="color:#e2e8f0">종목</b> — 미국 대형주 중심
</div>
</div>

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">📊 백테스트 성과 (2010~2025)</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">CAGR +11.5%</span> <span style="color:#475569;font-size:0.78rem">vs SPY +14.4%</span><br>
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">MDD -23.5%</span> <span style="color:#475569;font-size:0.78rem">vs SPY -33.7%</span><br>
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">Sharpe 0.75</span> <span style="color:#475569;font-size:0.78rem">vs SPY 0.84</span><br>
<span style="color:#eab308;font-family:Space Mono,monospace;font-weight:700">2022년 -9.9%</span> <span style="color:#475569;font-size:0.78rem">SPY 해당연도 -18%</span><br>
<span style="color:#94a3b8;font-size:0.78rem">승률 55.3% / 평균보유 10.4일</span>
</div>
</div>

</div>

<div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid #1e2a3a;font-size:0.72rem;color:#475569">
⚠️ 이 앱의 점수는 SPY 초과수익 전략이 아니라, <b>20거래일 스윙 관점 저낙폭 판단 보조 신호</b>입니다.
수익 확률이 아닌 기술적 적합도 점수이며, 투자 결정의 책임은 본인에게 있습니다.
</div>

</div>
""", unsafe_allow_html=True)

        st.info("👈 사이드바에서 종목명 또는 티커를 입력하고 **분석 실행**을 눌러주세요.")
        return

    # 데이터 로딩
    with st.spinner(f"{ticker} 분석 중..."):
        try:
            df  = fetch(ticker)
            f1_ok, tnx_change = check_f1()
        except Exception as e:
            st.error(f"데이터 로딩 실패: {e}")
            return

    if len(df) < 130:
        st.error("데이터 부족 (최소 130일 필요). 티커를 확인해주세요.")
        return

    # 지표 계산
    d   = compute(df)
    row = d.iloc[-1]
    close = float(row['Close'])
    atr   = float(row['atr']) if not pd.isna(row['atr']) else 0

    # G 점수
    g_raw, g_detail = g_score(row)
    scores = calc_scores(g_raw, f1_ok, avg_price if has_pos else None, close, atr)

    # ── 헤더 ──────────────────────────────────────────────
    h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
    with h1:
        mode_txt = "보유 종목 진단" if has_pos else "신규 매수 후보"
        mode_color = "#8b5cf6" if has_pos else "#3b82f6"
        st.markdown(f"""
        <div style='margin-bottom:0.3rem'>
            <span style='font-size:1.6rem;font-weight:700;color:#e2e8f0'>{ticker}</span>
            &nbsp;<span style='font-size:0.75rem;padding:2px 8px;border-radius:12px;
            background:#1e2a3a;color:{mode_color}'>{mode_txt}</span>
        </div>
        <div style='font-size:2rem;font-weight:700;color:#f1f5f9;font-family:Space Mono,monospace'>
            ${close:,.2f}
        </div>
        """, unsafe_allow_html=True)
    with h2:
        st.metric("RSI(14)", f"{row['rsi']:.1f}")
    with h3:
        st.metric("ATR(14)", f"{atr:.2f}")
    with h4:
        st.metric("거래량 비율", f"{row['vol_ratio']:.2f}x")

    st.divider()

    # ── F1 필터 상태 ───────────────────────────────────────
    if not np.isnan(tnx_change):
        if f1_ok:
            st.markdown(f'<div class="f1-box f1-ok">✅ 금리충격 필터 OFF — 매수 신호 활성 (10Y금리 60일 변화: {tnx_change:+.2f}%p)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="f1-box f1-warn">⚠️ 금리충격 필터 ON — 신규 매수 비활성 (10Y금리 60일 변화: {tnx_change:+.2f}%p ＞ +0.75%p)</div>', unsafe_allow_html=True)

    # ── 점수 카드 ─────────────────────────────────────────
    st.markdown(f"""
    <div class="score-wrap">
        <div class="score-card card-buy">
            <div class="score-label">매수 적합도</div>
            <div class="score-num-buy">{scores['buy']}%</div>
            <div class="score-sub">스윙 진입 신호</div>
        </div>
        <div class="score-card card-hold">
            <div class="score-label">홀딩 적합도</div>
            <div class="score-num-hold">{scores['hold']}%</div>
            <div class="score-sub">현 포지션 유지</div>
        </div>
        <div class="score-card card-sell">
            <div class="score-label">매도/관망</div>
            <div class="score-num-sell">{scores['sell']}%</div>
            <div class="score-sub">진입 보류 신호</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 판정 배너
    v = scores['verdict']
    cls_map = {'buy':'verdict-buy','hold':'verdict-hold','sell':'verdict-sell','filter':'verdict-filter'}
    st.markdown(f'<div class="verdict-banner {cls_map[v]}">{scores["verdict_text"]}</div>', unsafe_allow_html=True)

    # ── 탭 ────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 차트", "🔢 신호 상세", "🛡️ 손절 관리", "🔍 전종목 스캐너"])

    with tab1:
        fig = make_chart(df, ticker, avg_price if has_pos else None, atr)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-hdr">G 신호 구성 요소</div>', unsafe_allow_html=True)
            rows_html = ""
            for name, pts, kind in g_detail:
                pts_str = f"{pts:+d}점" if pts != 0 else "0점"
                rows_html += ind_row(name, pts_str, '긍정' if kind=='pos' else ('부정' if kind=='neg' else '중립'), kind)
            st.markdown(rows_html, unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right;font-size:0.8rem;color:#3b82f6;margin-top:6px'>G 원점수: {g_raw:+.0f}</div>", unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="sec-hdr">주요 가격 지표</div>', unsafe_allow_html=True)
            rows2 = ""
            rows2 += ind_row("SMA20", f"{row['sma20']:.2f}", '위' if close > row['sma20'] else '아래', 'pos' if close > row['sma20'] else 'neg')
            rows2 += ind_row("SMA60", f"{row['sma60']:.2f}", '위' if close > row['sma60'] else '아래', 'pos' if close > row['sma60'] else 'neg')
            rows2 += ind_row("SMA200", f"{row['sma200']:.2f}", '위' if close > row['sma200'] else '아래', 'pos' if close > row['sma200'] else 'neg')
            rows2 += ind_row("RSI(14)", f"{row['rsi']:.1f}", '과매도' if row['rsi']<30 else ('과매수' if row['rsi']>70 else '중립'), 'pos' if row['rsi']<30 else ('neg' if row['rsi']>70 else 'neu'))
            rows2 += ind_row("MACD Hist", f"{row['macd_hist']:+.3f}", '양수' if row['macd_hist']>0 else '음수', 'pos' if row['macd_hist']>0 else 'neg')
            rows2 += ind_row("거래량 비율", f"{row['vol_ratio']:.2f}x", '증가' if row['vol_ratio']>1.2 else ('감소' if row['vol_ratio']<0.8 else '보통'), 'pos' if row['vol_ratio']>1.2 else 'neu')
            bb_pos = (close - row['bb_lower']) / (row['bb_upper'] - row['bb_lower']) if (row['bb_upper'] - row['bb_lower']) > 0 else 0.5
            rows2 += ind_row("BB 위치", f"{bb_pos*100:.0f}%", '하단' if bb_pos<0.3 else ('상단' if bb_pos>0.7 else '중간'), 'pos' if bb_pos<0.3 else ('neg' if bb_pos>0.7 else 'neu'))
            st.markdown(rows2, unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="sec-hdr">ATR 기반 손절 기준 (v1b 전략)</div>', unsafe_allow_html=True)

        sl_8pct = close * 0.92
        tp_15   = close * 1.15
        tp_25   = close * 1.25

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""<div class="sl-box">
            <div style='color:#64748b;font-size:0.7rem;margin-bottom:4px'>손절선 (-8%)</div>
            <div style='color:#ef4444;font-size:1.2rem;font-weight:700'>${sl_8pct:.2f}</div>
            </div>""", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""<div class="sl-box">
            <div style='color:#64748b;font-size:0.7rem;margin-bottom:4px'>1차 목표 (+15%)</div>
            <div style='color:#22c55e;font-size:1.2rem;font-weight:700'>${tp_15:.2f}</div>
            </div>""", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""<div class="sl-box">
            <div style='color:#64748b;font-size:0.7rem;margin-bottom:4px'>2차 목표 (+25%)</div>
            <div style='color:#22c55e;font-size:1.2rem;font-weight:700'>${tp_25:.2f}</div>
            </div>""", unsafe_allow_html=True)

        if has_pos and avg_price:
            st.markdown('<div class="sec-hdr">보유 종목 손익 진단</div>', unsafe_allow_html=True)
            pnl_pct = (close - avg_price) / avg_price * 100
            sl_from_entry = avg_price * 0.92
            color = '#22c55e' if pnl_pct >= 0 else '#ef4444'
            sl_triggered = close <= sl_from_entry

            st.markdown(f"""
            <div class="sl-box">
                <div style='display:flex;justify-content:space-between;margin-bottom:8px'>
                    <span style='color:#64748b'>평균 매수가</span>
                    <span style='font-weight:600'>${avg_price:.2f}</span>
                </div>
                <div style='display:flex;justify-content:space-between;margin-bottom:8px'>
                    <span style='color:#64748b'>현재가</span>
                    <span style='font-weight:600'>${close:.2f}</span>
                </div>
                <div style='display:flex;justify-content:space-between;margin-bottom:8px'>
                    <span style='color:#64748b'>수익률</span>
                    <span style='color:{color};font-weight:700'>{pnl_pct:+.2f}%</span>
                </div>
                <div style='display:flex;justify-content:space-between'>
                    <span style='color:#64748b'>손절선 (매수가 -8%)</span>
                    <span style='color:#ef4444;font-weight:600'>${sl_from_entry:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if sl_triggered:
                st.markdown('<div class="verdict-banner verdict-sell">⚠️ 손절선 이탈 — 즉시 매도 또는 포지션 재검토 필요</div>', unsafe_allow_html=True)
            elif pnl_pct >= 15:
                st.markdown('<div class="verdict-banner verdict-hold">💡 +15% 목표 도달 — 분할 익절 또는 트레일링 스탑 고려</div>', unsafe_allow_html=True)


    with tab4:
        st.markdown('<div class="sec-hdr">전종목 매수 적합도 스캐너</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.82rem;color:#475569;margin-bottom:1rem'>"
            "G_US_F1 신호 기반 — 매수 적합도 순위표. 매 10분 캐시 갱신.</div>",
            unsafe_allow_html=True
        )

        sc_col1, sc_col2 = st.columns(2)

        for col_, market_, label_ in [(sc_col1,'US','🇺🇸 미국주식'), (sc_col2,'KR','🇰🇷 국내주식')]:
            with col_:
                st.markdown(f"**{label_}**")
                with st.spinner(f"{label_} 스캔 중... (30~60초 소요)"):
                    df_scan = scan_market(market_)

                if df_scan.empty:
                    st.warning("데이터를 가져오지 못했습니다.")
                    continue

                # 90% 이상 하이라이트
                top_picks = df_scan[df_scan['buy_pct'] >= 60]

                if not top_picks.empty:
                    st.markdown(
                        f"<div style='background:#0f2d1a;border:1px solid #166534;"
                        f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.8rem;"
                        f"font-size:0.82rem;color:#86efac'>"
                        f"🎯 매수 적합도 60% 이상: "
                        f"<b>{', '.join(top_picks['name'].tolist())}</b></div>",
                        unsafe_allow_html=True
                    )

                # 순위표 렌더링
                for _, r in df_scan.iterrows():
                    buy = r['buy_pct']
                    if buy >= 60:
                        bar_color = '#22c55e'
                        bg_color  = '#0a1a0f'
                        border    = '#166534'
                    elif buy >= 40:
                        bar_color = '#eab308'
                        bg_color  = '#1a1500'
                        border    = '#92400e'
                    else:
                        bar_color = '#ef4444'
                        bg_color  = '#0f1623'
                        border    = '#1e2a3a'

                    st.markdown(f"""
                    <div style="background:{bg_color};border:1px solid {border};
                        border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:6px">
                        <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:5px">
                            <div>
                                <span style="font-weight:600;color:#e2e8f0;font-size:0.9rem">{r['name']}</span>
                                <span style="color:#475569;font-size:0.75rem;margin-left:6px">{r['ticker']}</span>
                            </div>
                            <div style="font-family:Space Mono,monospace;font-size:0.82rem;color:#94a3b8">
                                ${r['close']:,.2f} &nbsp;|&nbsp; RSI {r['rsi']}
                            </div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px">
                            <div style="flex:1;background:#1e2a3a;border-radius:4px;height:6px;overflow:hidden">
                                <div style="background:{bar_color};width:{buy}%;height:6px;border-radius:4px"></div>
                            </div>
                            <span style="font-family:Space Mono,monospace;font-weight:700;
                                color:{bar_color};font-size:0.88rem;min-width:36px;text-align:right">{buy}%</span>
                            <span style="color:#475569;font-size:0.72rem;min-width:28px">매수</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


    # 면책 고지
    st.markdown("""
    <div class="disclaimer">
    ⚠️ <b>투자 유의사항:</b> 이 앱의 점수는 G_US_F1 백테스트(2010~2025) 기반 기술적 적합도 점수이며,
    실제 수익률을 보장하지 않습니다. 과거 성과(CAGR +11.5%, MDD -23.5%)는 미래 성과를 보장하지 않으며,
    개별 종목 결과는 포트폴리오 전체 백테스트 결과와 다를 수 있습니다.
    투자 결정의 최종 책임은 본인에게 있습니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
