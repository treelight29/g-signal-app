"""
Luna-Signal v0.1 — 스윙 매수 적합도 앱
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
import warnings, json
warnings.filterwarnings('ignore')

# Google Sheets 연동
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_OK = True
except ImportError:
    GSHEETS_OK = False

# ══════════════════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Luna-Signal",
    page_icon="🌙",
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

    # 종목명 입력 시 티커로 그대로 사용 (API 키 없음)
    # 티커 직접 입력 필요: AAPL, 005930.KS 등
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


def calc_scores_from_percentile(pct: float, f1_ok: bool,
                                avg_price: float, close: float) -> dict:
    """
    유니버스 백분위 → 매수/홀딩/매도 % 변환
    pct: 0~100 (높을수록 유니버스 내 상위)
    백테스트와 동일한 상대순위 기반 (3자 합의: Claude+GPT+Gemini)

    기준:
      상위 10% (pct >= 90): 강한 매수 후보
      상위 20% (pct >= 80): 매수 후보
      상위 40% (pct >= 60): 보유 가능
      상위 40% 밖 (pct < 60): 신규매수 부적합
    """
    # F1 필터 ON → 매수 상한 20점
    if not f1_ok:
        return {
            'buy': 5, 'hold': 15, 'sell': 80,
            'percentile': pct,
            'verdict': 'filter',
            'verdict_text': '⚠️ 금리충격 필터 ON — 신규 매수 비활성화 (10년물 금리 급등 구간)'
        }

    # 백분위 기반 매수 점수
    buy_score  = pct                          # 백분위 그대로
    sell_score = max(0, (100 - pct) * 0.6)
    hold_score = max(0, 100 - buy_score - sell_score)

    total = buy_score + hold_score + sell_score
    if total == 0: total = 1
    buy_pct  = round(buy_score  / total * 100)
    hold_pct = round(hold_score / total * 100)
    sell_pct = round(100 - buy_pct - hold_pct)

    # 보유 종목 손절 반영
    if avg_price and avg_price > 0:
        pnl = (close - avg_price) / avg_price
        if pnl <= -0.08:
            return {
                'buy': 0, 'hold': 10, 'sell': 90,
                'percentile': pct,
                'verdict': 'sell',
                'verdict_text': '🚨 손절선 -8% 이탈 — 즉시 매도 검토'
            }
        elif pnl <= -0.05:
            sell_pct = min(100, sell_pct + 20)
            buy_pct  = max(0,  buy_pct  - 15)
            hold_pct = 100 - buy_pct - sell_pct
        elif pnl >= 0.15:
            sell_pct = min(100, sell_pct + 15)
            buy_pct  = max(0,  buy_pct  - 10)
            hold_pct = 100 - buy_pct - sell_pct

    # 판정
    if pct >= 90:
        verdict = 'buy'
        verdict_text = '🟢 강한 매수 후보 — 유니버스 상위 10%, 20거래일 스윙 진입 적합'
    elif pct >= 80:
        verdict = 'buy'
        verdict_text = '🟢 매수 후보 — 유니버스 상위 20%, 진입 고려 가능'
    elif pct >= 60:
        verdict = 'hold'
        verdict_text = '🟡 보유 가능 — 유니버스 상위 40%, 신규 진입보다 기존 보유 유지'
    else:
        verdict = 'sell'
        verdict_text = '🔴 신규매수 부적합 — 유니버스 하위 60%, 관망 권장'

    return {
        'buy': buy_pct, 'hold': hold_pct, 'sell': sell_pct,
        'percentile': round(pct, 1),
        'verdict': verdict, 'verdict_text': verdict_text
    }


def calc_scores(g_raw: float, f1_ok: bool,
                avg_price: float, close: float, atr: float,
                universe_pct: float = None) -> dict:
    """
    하위 호환용 래퍼 — 단일 종목 조회 시 universe_pct 없으면
    G 원점수를 임시 백분위로 변환 (스캔 후 재계산 권장)
    """
    if universe_pct is not None:
        return calc_scores_from_percentile(universe_pct, f1_ok, avg_price, close)

    # 단일 종목 조회 시: G 원점수 기반 임시 백분위 (±65~110 범위 정규화)
    tmp_pct = (g_raw + 65) / 175 * 100
    tmp_pct = max(0.0, min(100.0, tmp_pct))
    return calc_scores_from_percentile(tmp_pct, f1_ok, avg_price, close)



# ══════════════════════════════════════════════════════════
# 스캐너 종목 리스트
# ══════════════════════════════════════════════════════════
SCAN_US = {
    # IT/반도체
    'AAPL':'Apple', 'MSFT':'Microsoft', 'NVDA':'NVIDIA', 'AVGO':'Broadcom',
    'AMD':'AMD', 'INTC':'Intel', 'QCOM':'Qualcomm', 'TXN':'Texas Instruments',
    'MU':'Micron', 'AMAT':'Applied Materials', 'LRCX':'Lam Research',
    'KLAC':'KLA Corp', 'ADI':'Analog Devices', 'MRVL':'Marvell',
    'ORCL':'Oracle', 'CRM':'Salesforce', 'NOW':'ServiceNow', 'INTU':'Intuit',
    'ADBE':'Adobe', 'PANW':'Palo Alto', 'CRWD':'CrowdStrike',
    'FTNT':'Fortinet', 'IBM':'IBM', 'HPQ':'HP', 'DELL':'Dell',
    # 통신/미디어
    'GOOGL':'Alphabet', 'META':'Meta', 'NFLX':'Netflix', 'DIS':'Disney',
    'CMCSA':'Comcast', 'T':'AT&T', 'VZ':'Verizon', 'TMUS':'T-Mobile',
    # 임의소비재
    'AMZN':'Amazon', 'TSLA':'Tesla', 'HD':'Home Depot', 'LOW':"Lowe's",
    'TGT':'Target', 'WMT':'Walmart', 'COST':'Costco', 'MCD':"McDonald's",
    'SBUX':'Starbucks', 'NKE':'Nike', 'BKNG':'Booking', 'UBER':'Uber',
    # 필수소비재
    'PG':'P&G', 'KO':'Coca-Cola', 'PEP':'PepsiCo', 'PM':'Philip Morris',
    'MO':'Altria', 'CL':'Colgate', 'GIS':'General Mills', 'SYY':'Sysco',
    # 헬스케어
    'LLY':'Eli Lilly', 'JNJ':'J&J', 'UNH':'UnitedHealth', 'ABBV':'AbbVie',
    'MRK':'Merck', 'PFE':'Pfizer', 'BMY':'BMS', 'AMGN':'Amgen',
    'GILD':'Gilead', 'REGN':'Regeneron', 'VRTX':'Vertex', 'ISRG':'Intuitive',
    'SYK':'Stryker', 'MDT':'Medtronic', 'ABT':'Abbott', 'BSX':'Boston Sci',
    'TMO':'Thermo Fisher', 'DHR':'Danaher',
    # 금융
    'JPM':'JPMorgan', 'BAC':'BofA', 'WFC':'Wells Fargo', 'GS':'Goldman',
    'MS':'Morgan Stanley', 'C':'Citigroup', 'AXP':'AmEx', 'BLK':'BlackRock',
    'SCHW':'Schwab', 'V':'Visa', 'MA':'Mastercard', 'PYPL':'PayPal',
    'COF':'Capital One', 'USB':'US Bancorp', 'PNC':'PNC Financial',
    'CB':'Chubb', 'PGR':'Progressive',
    # 에너지
    'XOM':'ExxonMobil', 'CVX':'Chevron', 'COP':'ConocoPhillips',
    'EOG':'EOG Resources', 'SLB':'SLB', 'MPC':'Marathon Pet',
    'PSX':'Phillips 66', 'VLO':'Valero', 'OXY':'Occidental',
    # 산업재
    'CAT':'Caterpillar', 'HON':'Honeywell', 'UPS':'UPS', 'RTX':'RTX',
    'LMT':'Lockheed', 'BA':'Boeing', 'GE':'GE', 'MMM':'3M',
    'DE':'Deere', 'ETN':'Eaton', 'FDX':'FedEx', 'UNP':'Union Pacific',
    'WM':'Waste Mgmt', 'NSC':'Norfolk Southern', 'CSX':'CSX',
    # 소재
    'LIN':'Linde', 'APD':'Air Products', 'SHW':'Sherwin-Williams',
    'ECL':'Ecolab', 'NEM':'Newmont', 'FCX':'Freeport', 'NUE':'Nucor',
    # 유틸리티
    'NEE':'NextEra', 'DUK':'Duke Energy', 'SO':'Southern', 'D':'Dominion',
    'AEP':'AEP', 'EXC':'Exelon', 'SRE':'Sempra',
    # 부동산
    'AMT':'American Tower', 'PLD':'Prologis', 'EQIX':'Equinix',
    'CCI':'Crown Castle', 'SPG':'Simon Property', 'O':'Realty Income',
}

SCAN_KR = {
    # 반도체/IT
    '005930.KS':'삼성전자', '000660.KS':'SK하이닉스', '009150.KS':'삼성전기',
    '066570.KS':'LG전자', '034730.KS':'SK', '018260.KS':'삼성SDS',
    '035420.KS':'NAVER', '035720.KS':'카카오', '036570.KS':'엔씨소프트',
    # 자동차/기계/조선
    '005380.KS':'현대차', '000270.KS':'기아', '012330.KS':'현대모비스',
    '064350.KS':'현대로템', '042660.KS':'한화오션', '009540.KS':'HD한국조선해양',
    '010140.KS':'삼성중공업', '329180.KS':'HD현대', '241560.KS':'두산밥캣',
    # 화학/배터리/소재
    '051910.KS':'LG화학', '006400.KS':'삼성SDI', '096770.KS':'SK이노베이션',
    '011170.KS':'롯데케미칼', '010950.KS':'S-Oil', '010130.KS':'고려아연',
    '004020.KS':'현대제철', '005490.KS':'POSCO홀딩스', '003670.KS':'포스코퓨처엠',
    '247540.KS':'에코프로비엠', '086520.KS':'에코프로',
    # 금융
    '105560.KS':'KB금융', '055550.KS':'신한지주', '086790.KS':'하나금융',
    '032830.KS':'삼성생명', '000810.KS':'삼성화재', '316140.KS':'우리금융',
    '024110.KS':'기업은행',
    # 통신
    '017670.KS':'SK텔레콤', '030200.KS':'KT', '032640.KS':'LG유플러스',
    # 유통/소비재
    '028260.KS':'삼성물산', '003550.KS':'LG', '069960.KS':'현대백화점',
    '004170.KS':'신세계', '023530.KS':'롯데쇼핑', '271560.KS':'오리온',
    '097950.KS':'CJ제일제당', '001040.KS':'CJ',
    # 건설/엔지니어링
    '000720.KS':'현대건설', '028050.KS':'삼성엔지니어링', '034020.KS':'두산에너빌리티',
    # 바이오/헬스
    '068270.KS':'셀트리온', '207940.KS':'삼성바이오로직스', '128940.KS':'한미약품',
    '000100.KS':'유한양행', '185750.KS':'종근당',
    # 항공/물류
    '003490.KS':'대한항공', '011200.KS':'HMM', '000120.KS':'CJ대한통운',
}


@st.cache_data(ttl=600)
def scan_market(market: str) -> pd.DataFrame:
    """
    전체 종목 스캔 — G 원점수 계산 후 유니버스 백분위 변환
    백테스트와 동일한 상대순위 기반 (3자 합의)
    """
    tickers = SCAN_US if market == 'US' else SCAN_KR
    f1_ok, tnx_change = check_f1()

    # 1단계: 전 종목 G 원점수 수집
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
            close    = float(row['Close'])
            atr_val  = float(row['atr']) if not pd.isna(row['atr']) else 0
            g_raw, _ = g_score(row)
            rows.append({
                'ticker':    ticker,
                'name':      name,
                'close':     close,
                'g_raw':     g_raw,
                'rsi':       round(row['rsi'], 1) if not pd.isna(row['rsi']) else None,
                'vol_ratio': round(row['vol_ratio'], 2) if not pd.isna(row['vol_ratio']) else None,
                'sma20_ok':  int(row['Close'] > row['sma20']) if not pd.isna(row['sma20']) else 0,
                'date':      d.index[-1].strftime('%Y-%m-%d'),
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df_all = pd.DataFrame(rows)

    # 2단계: 유니버스 내 백분위 계산 (핵심 — 백테스트와 동일한 상대순위)
    g_series = df_all['g_raw']
    df_all['percentile'] = g_series.rank(pct=True) * 100  # 0~100

    # 3단계: 백분위 → 매수/홀딩/매도 점수 변환
    def row_to_scores(r):
        sc = calc_scores_from_percentile(r['percentile'], f1_ok, None, r['close'])
        return pd.Series({
            'buy_pct':    sc['buy'],
            'hold_pct':   sc['hold'],
            'sell_pct':   sc['sell'],
            'verdict':    sc['verdict'],
        })

    scores = df_all.apply(row_to_scores, axis=1)
    df_all = pd.concat([df_all, scores], axis=1)

    df_result = df_all.sort_values('percentile', ascending=False).reset_index(drop=True)
    df_result['rank'] = range(1, len(df_result) + 1)
    df_result['total'] = len(df_result)
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
        st.markdown("## 🌙 Luna-Signal")
        st.markdown("<div style='font-size:0.78rem;color:#475569;margin-bottom:1rem'>스윙 매수 적합도 분석 v1.0</div>", unsafe_allow_html=True)
        st.divider()

        # ★ 홈화면 돋보기 버튼 클릭 시 자동 입력
        default_query = st.session_state.pop('quick_ticker_input', 'AAPL')

        query = st.text_input(
            "종목명 또는 티커",
            value=default_query,
            key="main_query",
            help="종목명: 삼성전자, 애플, NVIDIA / 티커: AAPL, 005930.KS"
        ).strip()

        # 종목명 → 티커 변환
        ticker, resolved_name = resolve_ticker(query)

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

        # ★ 분석 실행 버튼 클릭 시 quick_ticker 세션 정리
        if run:
            st.session_state.pop('quick_ticker', None)
            st.session_state.pop('quick_name', None)

        st.markdown("""
        <div style='font-size:0.72rem;color:#334155;margin-top:1.5rem;line-height:1.7'>
        <b>신호 엔진 정보 (v1.0)</b><br>
        · G_US_F1 + G2-3 개선 적용<br>
        · MDD -26.0% (SPY -33.7%)<br>
        · 최대 30거래일 스윙<br>
        · -8% 손절 + 트레일링<br>
        · 금리충격 필터 연동
        </div>
        """, unsafe_allow_html=True)

    return ticker, resolved_name, has_pos, avg_price, run


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════
def _save_portfolio():
    """보유종목을 localStorage에 저장 (브라우저 영구 저장)"""
    import json
    data = json.dumps(st.session_state.portfolio, ensure_ascii=False)
    # st.components로 localStorage 저장
    import streamlit.components.v1 as components
    components.html(f"""
    <script>
    try {{
        localStorage.setItem('luna_portfolio', {repr(data)});
    }} catch(e) {{}}
    </script>
    """, height=0)

def _load_portfolio():
    """localStorage에서 보유종목 불러오기"""
    import streamlit.components.v1 as components
    import json
    # localStorage 읽기 + hidden input으로 전달
    components.html("""
    <script>
    try {
        var d = localStorage.getItem('luna_portfolio');
        if (d) {
            var el = window.parent.document.querySelector('[data-testid="stHidden"]');
        }
    } catch(e) {}
    </script>
    """, height=0)

# ══════════════════════════════════════════════════════════
# Google Sheets 연동 함수
# ══════════════════════════════════════════════════════════

@st.cache_resource
def get_gsheet():
    """Google Sheets 연결 (캐시)"""
    if not GSHEETS_OK:
        return None
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet_id = st.secrets.get("GOOGLE_SHEETS_ID", "")
        if not sheet_id:
            return None
        sh = client.open_by_key(sheet_id)
        # 시트1 사용 (없으면 생성)
        try:
            ws = sh.worksheet("보유종목")
        except:
            ws = sh.add_worksheet("보유종목", rows=200, cols=15)
            # 헤더 추가
            ws.append_row([
                "ticker","name","avg_price","shares",
                "curr_price","curr_date","sl_price","tp1_price","tp2_price"
            ])
        return ws
    except Exception as e:
        st.session_state['sheets_error'] = str(e)
        return None


def load_portfolio_from_sheets():
    """Google Sheets에서 보유종목 로드"""
    ws = get_gsheet()
    if ws is None:
        return []
    try:
        records = ws.get_all_records()
        portfolio = []
        for r in records:
            if not r.get('ticker'):
                continue
            portfolio.append({
                'ticker':     str(r.get('ticker', '')),
                'name':       str(r.get('name', '')),
                'avg_price':  float(r.get('avg_price', 0)),
                'shares':     int(r.get('shares', 0)),
                'curr_price': float(r.get('curr_price', 0)),
                'curr_date':  str(r.get('curr_date', '-')),
                'sl_price':   float(r.get('sl_price', 0)),
                'tp1_price':  float(r.get('tp1_price', 0)),
                'tp2_price':  float(r.get('tp2_price', 0)),
            })
        return portfolio
    except:
        return []


def save_portfolio_to_sheets(portfolio):
    """보유종목 전체를 Google Sheets에 저장"""
    ws = get_gsheet()
    if ws is None:
        return False
    try:
        # 기존 데이터 삭제 (헤더 제외)
        ws.clear()
        ws.append_row([
            "ticker","name","avg_price","shares",
            "curr_price","curr_date","sl_price","tp1_price","tp2_price"
        ])
        for pos in portfolio:
            ws.append_row([
                pos.get('ticker',''),
                pos.get('name',''),
                pos.get('avg_price', 0),
                pos.get('shares', 0),
                pos.get('curr_price', 0),
                pos.get('curr_date', '-'),
                pos.get('sl_price', 0),
                pos.get('tp1_price', 0),
                pos.get('tp2_price', 0),
            ])
        return True
    except:
        return False


def _render_portfolio_tab():
    """보유종목 관리 — 홈화면 및 탭6 공통 사용"""
    import json

    # ── 세션 초기화 및 localStorage 복원 ──────────────────
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
        st.session_state['portfolio_loaded'] = False

    # localStorage 저장/복원 컴포넌트
    import streamlit.components.v1 as components

    # 저장된 데이터 로드 (최초 1회)
    if not st.session_state.get('portfolio_loaded', False):
        result = components.html("""
        <script>
        var stored = localStorage.getItem('luna_portfolio');
        if (stored) {
            // Streamlit에 데이터 전달
            window.parent.postMessage({type: 'luna_portfolio', data: stored}, '*');
        }
        </script>
        <div id="portfolio_data" style="display:none"></div>
        """, height=0)
        st.session_state['portfolio_loaded'] = True

    # ── 안내 문구 ──────────────────────────────────────────
    sheets_ok_tab = get_gsheet() is not None
    if sheets_ok_tab:
        st.markdown("<div class='f1-box f1-ok'>✅ Google Sheets 연동됨 — 보유종목 자동 저장/복원</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='f1-box f1-warn'>⚠️ Google Sheets 미연결 — 세션 종료 시 초기화됩니다</div>", unsafe_allow_html=True)
        err = st.session_state.get('sheets_error', '')
        if err:
            st.error(f"🔍 오류 내용: {err}")
    st.markdown("<div style='font-size:0.82rem;color:#475569;margin-bottom:1rem'>보유 종목 등록 시 손절선(-8%)과 현재 손익을 모니터링합니다.</div>", unsafe_allow_html=True)

    # ── 종목 추가 폼 ──────────────────────────────────────
    st.markdown('<div class="sec-hdr">종목 추가</div>', unsafe_allow_html=True)
    with st.form("add_portfolio_form", clear_on_submit=True):
        p1, p2, p3, p4 = st.columns([2, 1.5, 1.5, 1])
        with p1:
            new_ticker = st.text_input("티커 또는 종목명",
                                        placeholder="AAPL, 삼성전자 등")
        with p2:
            new_price  = st.number_input("평균 매수가", min_value=0.01,
                                          value=100.0, step=0.01)
        with p3:
            new_shares = st.number_input("수량 (주)", min_value=1,
                                          value=10, step=1)
        with p4:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            add_btn = st.form_submit_button("➕ 추가", use_container_width=True)

    if add_btn and new_ticker.strip():
        resolved_t, resolved_n = resolve_ticker(new_ticker.strip())
        if resolved_t != 'UNKNOWN':
            try:
                df_p = fetch(resolved_t, days=10)
                curr_p    = float(df_p['Close'].iloc[-1]) if len(df_p) > 0 else new_price
                curr_date = df_p.index[-1].strftime('%Y-%m-%d') if len(df_p) > 0 else '-'
            except:
                curr_p    = new_price
                curr_date = '-'

            new_pos = {
                'ticker':     resolved_t,
                'name':       resolved_n,
                'avg_price':  new_price,
                'shares':     new_shares,
                'curr_price': curr_p,
                'curr_date':  curr_date,
                'sl_price':   round(new_price * 0.92, 2),
                'tp1_price':  round(new_price * 1.15, 2),
                'tp2_price':  round(new_price * 1.25, 2),
            }
            st.session_state.portfolio.append(new_pos)
            with st.spinner("Google Sheets에 저장 중..."):
                ok = save_portfolio_to_sheets(st.session_state.portfolio)
            st.success(f"✅ {resolved_n} ({resolved_t}) {'저장 완료' if ok else '추가됨 (시트 저장 실패)'}")
            st.rerun()
        else:
            st.error("종목을 찾지 못했습니다. 티커를 직접 입력해주세요.")

    # ── 보유종목 테이블 ───────────────────────────────────
    if not st.session_state.portfolio:
        st.info("보유 종목이 없습니다. 위에서 종목을 추가해주세요.")
    else:
        col_r1, col_r2 = st.columns([1, 5])
        with col_r1:
            if st.button("🔄 현재가 갱신", use_container_width=True):
                for pos in st.session_state.portfolio:
                    try:
                        df_p = fetch(pos['ticker'], days=10)
                        if len(df_p) > 0:
                            pos['curr_price'] = float(df_p['Close'].iloc[-1])
                            pos['curr_date']  = df_p.index[-1].strftime('%Y-%m-%d')
                    except:
                        pass
                # 갱신 후 저장
                save_portfolio_to_sheets(st.session_state.portfolio)
                st.rerun()



        st.divider()

        # 포트폴리오 요약
        total_cost    = sum(p['avg_price'] * p['shares'] for p in st.session_state.portfolio)
        total_curr    = sum(p['curr_price'] * p['shares'] for p in st.session_state.portfolio)
        total_pnl     = total_curr - total_cost
        total_pnl_pct = (total_curr / total_cost - 1) * 100 if total_cost > 0 else 0

        s1, s2, s3, s4 = st.columns(4)
        with s1: st.metric("보유 종목 수", f"{len(st.session_state.portfolio)}개")
        with s2: st.metric("총 매수금액", f"${total_cost:,.0f}")
        with s3: st.metric("총 평가금액", f"${total_curr:,.0f}")
        with s4: st.metric("총 손익", f"{total_pnl_pct:+.2f}%",
                            delta=f"${total_pnl:+,.0f}")

        st.divider()

        # 종목별 카드
        for idx_p, pos in enumerate(st.session_state.portfolio):
            pnl_pct = (pos['curr_price'] / pos['avg_price'] - 1) * 100
            pnl_amt = (pos['curr_price'] - pos['avg_price']) * pos['shares']
            is_sl   = pos['curr_price'] <= pos['sl_price']
            is_tp1  = pos['curr_price'] >= pos['tp1_price']
            sl_gap  = (pos['curr_price'] / pos['sl_price'] - 1) * 100

            if is_sl:
                card_bg='#1a0a0a'; card_bdr='#ef4444'
                status=f"⚠️ 손절선 이탈"; st_color='#ef4444'
            elif is_tp1:
                card_bg='#0f2d1a'; card_bdr='#22c55e'
                status=f"🎯 1차 목표 달성"; st_color='#22c55e'
            else:
                card_bg='#0f1623'; card_bdr='#1e2a3a'
                status=f"{'▲' if pnl_pct>=0 else '▼'} {pnl_pct:+.2f}%"
                st_color='#22c55e' if pnl_pct>=0 else '#ef4444'

            st.markdown(f"""
            <div style="background:{card_bg};border:1px solid {card_bdr};
                border-radius:10px;padding:1rem 1.2rem;margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;
                    align-items:center;margin-bottom:10px">
                    <div>
                        <span style="font-weight:700;color:#e2e8f0;font-size:1rem">{pos['name']}</span>
                        <span style="color:#475569;font-size:0.78rem;margin-left:8px">{pos['ticker']}</span>
                        <span style="color:#334155;font-size:0.72rem;margin-left:8px">{pos['shares']}주</span>
                    </div>
                    <span style="color:{st_color};font-weight:700">{status}</span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;
                    font-family:Space Mono,monospace;font-size:0.82rem">
                    <div><div style="color:#475569;font-size:0.68rem;margin-bottom:2px">평균매수가</div>
                        <div style="color:#94a3b8">${pos['avg_price']:.2f}</div></div>
                    <div><div style="color:#475569;font-size:0.68rem;margin-bottom:2px">현재가({pos['curr_date']})</div>
                        <div style="color:#e2e8f0;font-weight:600">${pos['curr_price']:.2f}</div></div>
                    <div><div style="color:#475569;font-size:0.68rem;margin-bottom:2px">손절선(-8%)</div>
                        <div style="color:#ef4444">${pos['sl_price']:.2f}
                        <span style="font-size:0.68rem;color:#64748b">({sl_gap:+.1f}%)</span></div></div>
                    <div><div style="color:#475569;font-size:0.68rem;margin-bottom:2px">1차목표(+15%)</div>
                        <div style="color:#22c55e">${pos['tp1_price']:.2f}</div></div>
                    <div><div style="color:#475569;font-size:0.68rem;margin-bottom:2px">평가손익</div>
                        <div style="color:{'#22c55e' if pnl_amt>=0 else '#ef4444'};font-weight:700">
                        ${pnl_amt:+,.0f}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)

            if is_sl:
                st.markdown('<div class="verdict-banner verdict-sell">⚠️ 손절선 이탈 — 즉시 매도 또는 포지션 재검토</div>', unsafe_allow_html=True)
            elif is_tp1:
                st.markdown('<div class="verdict-banner verdict-hold">💡 +15% 목표 달성 — 분할 익절 또는 트레일링 스탑 고려</div>', unsafe_allow_html=True)

            if st.button(f"🗑️ {pos['name']} 삭제", key=f"del_{idx_p}"):
                st.session_state.portfolio.pop(idx_p)
                # 삭제 후 저장
                with st.spinner("저장 중..."):
                    save_portfolio_to_sheets(st.session_state.portfolio)
                st.rerun()





        # 전체 초기화
        if st.button("🗑️ 전체 초기화", type="secondary"):
            st.session_state.portfolio = []
            with st.spinner("저장 중..."):
                save_portfolio_to_sheets([])
            st.rerun()





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
    # 세션 초기화 — Google Sheets에서 로드
    if 'portfolio' not in st.session_state:
        with st.spinner("보유종목 불러오는 중..."):
            st.session_state.portfolio = load_portfolio_from_sheets()
    if 'sheets_ok' not in st.session_state:
        st.session_state.sheets_ok = get_gsheet() is not None

    ticker, resolved_name, has_pos, avg_price, run = sidebar()

    # ★ 돋보기 버튼으로 분석 요청된 경우 ticker 덮어쓰기
    if 'analyze_ticker' in st.session_state and not run:
        ticker        = st.session_state['analyze_ticker']
        resolved_name = st.session_state.get('analyze_name', ticker)
        run           = True   # 분석 실행으로 처리

    st.markdown("# 🌙 Luna-Signal")
    st.markdown("<div style='color:#475569;font-size:0.9rem;margin-bottom:1.5rem'>20거래일 스윙 매수 적합도 분석 — G_US_F1 신호 엔진 v1.0</div>", unsafe_allow_html=True)

    if not run:
        # ── 기본화면: 전종목 스크리닝 상위 10개 ─────────────────
        st.markdown("""
<div style="font-size:0.68rem;letter-spacing:0.14em;text-transform:uppercase;
color:#3b82f6;font-weight:600;margin-bottom:0.8rem">
📡 실시간 매수 적합도 — 상위 10종목
</div>""", unsafe_allow_html=True)

        f1_ok_home, tnx_ch_home = check_f1()
        if not np.isnan(tnx_ch_home):
            if f1_ok_home:
                st.markdown(
                    f"<div class='f1-box f1-ok'>✅ 금리충격 필터 OFF — 매수 신호 활성 "
                    f"(10Y금리 60일 변화: {tnx_ch_home:+.2f}%p)</div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='f1-box f1-warn'>⚠️ 금리충격 필터 ON — 신규 매수 비활성 "
                    f"(10Y금리 60일 변화: {tnx_ch_home:+.2f}%p ＞ +0.75%p)</div>",
                    unsafe_allow_html=True)

        home_tab_us, home_tab_kr = st.tabs(["🇺🇸 미국주식 Top10", "🇰🇷 국내주식 Top10"])

        for home_tab, home_market, home_label in [
            (home_tab_us, 'US', '미국'),
            (home_tab_kr, 'KR', '국내'),
        ]:
            with home_tab:
                with st.spinner(f"{home_label} 종목 스캔 중..."):
                    df_home = scan_market(home_market)

                if df_home.empty:
                    st.warning("데이터를 가져오지 못했습니다.")
                    continue

                top10 = df_home.head(10)

                # 테이블 헤더
                st.markdown("""
                <div style="display:grid;grid-template-columns:40px 80px 110px 100px 70px 70px 70px;
                    gap:4px;padding:6px 8px;background:#0f1623;border-radius:6px;
                    font-size:0.7rem;letter-spacing:0.08em;text-transform:uppercase;
                    color:#475569;font-weight:600;margin-bottom:4px">
                    <div>순위</div><div>티커</div><div>종목명</div>
                    <div>현재가</div>
                    <div style="text-align:center">매수</div>
                    <div style="text-align:center">홀딩</div>
                    <div style="text-align:center">매도</div>
                </div>""", unsafe_allow_html=True)

                for _, r in top10.iterrows():
                    pct   = r['percentile']
                    buy_  = r['buy_pct']
                    hold_ = r['hold_pct']
                    sell_ = r['sell_pct']
                    rank_ = r['rank']

                    if pct >= 80:
                        bar_c = '#22c55e'; row_bg = '#0a1a0f'; row_bd = '#166534'
                        rank_c = '#22c55e'
                    elif pct >= 60:
                        bar_c = '#eab308'; row_bg = '#1a1500'; row_bd = '#92400e'
                        rank_c = '#eab308'
                    else:
                        bar_c = '#94a3b8'; row_bg = '#0f1623'; row_bd = '#1e2a3a'
                        rank_c = '#64748b'

                    price_str = f"${r['close']:,.2f}" if home_market == 'US' else f"₩{r['close']:,.0f}"

                    st.markdown(f"""
                    <div style="display:grid;grid-template-columns:40px 80px 110px 100px 70px 70px 70px;
                        gap:4px;padding:8px 8px;background:{row_bg};
                        border:1px solid {row_bd};border-radius:6px;margin-bottom:3px;align-items:center">
                        <div style="font-family:Space Mono,monospace;font-size:0.9rem;
                            font-weight:700;color:{rank_c}">#{rank_}</div>
                        <div style="font-family:Space Mono,monospace;font-size:0.75rem;
                            color:#94a3b8">{r['ticker']}</div>
                        <div style="font-size:0.85rem;font-weight:600;color:#e2e8f0">{r['name']}</div>
                        <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                            color:#64748b">{price_str}</div>
                        <div style="text-align:center;font-family:Space Mono,monospace;
                            font-weight:700;font-size:0.88rem;color:{bar_c}">{buy_}%</div>
                        <div style="text-align:center;font-family:Space Mono,monospace;
                            font-size:0.82rem;color:#eab308">{hold_}%</div>
                        <div style="text-align:center;font-family:Space Mono,monospace;
                            font-size:0.82rem;color:#ef4444">{sell_}%</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 종목 클릭 → 분석 실행 버튼
                    if st.button(f"🔍 {r['name']} 분석", key=f"home_{home_market}_{r['ticker']}",
                                  use_container_width=False):
                        st.session_state['analyze_ticker'] = r['ticker']
                        st.session_state['analyze_name']   = r['name']
                        st.rerun()

                st.markdown(
                    f"<div style='font-size:0.72rem;color:#334155;margin-top:0.5rem'>"
                    f"전체 {len(df_home)}종목 중 상위 10개 표시 · 10분 캐시</div>",
                    unsafe_allow_html=True)

        # 전략 개요 (접힌 형태)
        with st.expander("📋 전략 개요 보기"):
            st.markdown("""
<div style="background:#0f1623;border:1px solid #1e2a3a;border-radius:12px;padding:1.8rem 2rem;">
<div style="display:flex;gap:2rem;flex-wrap:wrap">

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">📋 개발 과정</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<b style="color:#e2e8f0">Phase 1</b> — 5개 전략 후보 신호 품질 검증<br>
<b style="color:#e2e8f0">Phase 1.5</b> — G 전략 실패 원인 진단<br>
<b style="color:#e2e8f0">Phase 2A</b> — SMA200 필터 테스트 → 실패<br>
<b style="color:#e2e8f0">Phase 2B</b> — 금리충격 필터(F1) 테스트 → 통과<br>
<b style="color:#e2e8f0">Phase G2-3</b> — 트레일링+점수연장 → v1.0 확정
</div>
</div>

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">⚙️ 전략 핵심 규칙</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<b style="color:#e2e8f0">신호</b> — 가격구조 + 거래량 (후행지표 최소화)<br>
<b style="color:#e2e8f0">필터</b> — 10년물 금리 60일 변화 ＞ +0.75%p 시 매수 중단<br>
<b style="color:#e2e8f0">손절</b> — 진입가 대비 -8% 고정<br>
<b style="color:#e2e8f0">보유</b> — 점수 유지 시 최대 30거래일<br>
<b style="color:#e2e8f0">종목</b> — 미국 대형주 중심
</div>
</div>

<div style="flex:1;min-width:220px">
<div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem">📊 백테스트 성과 (2010~2025)</div>
<div style="font-size:0.88rem;color:#cbd5e1;line-height:1.9">
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">CAGR +9.3%</span> <span style="color:#475569;font-size:0.78rem">vs SPY +14.4%</span><br>
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">MDD -26.0%</span> <span style="color:#475569;font-size:0.78rem">vs SPY -33.7%</span><br>
<span style="color:#22c55e;font-family:Space Mono,monospace;font-weight:700">Sharpe 0.70</span> <span style="color:#475569;font-size:0.78rem">vs SPY 0.84</span><br>
<span style="color:#eab308;font-family:Space Mono,monospace;font-weight:700">2022년 -23.2%</span> <span style="color:#475569;font-size:0.78rem">SPY 해당연도 -18%</span><br>
<span style="color:#94a3b8;font-size:0.78rem">승률 58.9% / 평균보유 21.8일</span>
</div>
</div>

</div>

<div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid #1e2a3a;font-size:0.72rem;color:#475569">
⚠️ 이 앱의 점수는 SPY 초과수익 전략이 아니라, <b>20거래일 스윙 관점 저낙폭 판단 보조 신호</b>입니다.
수익 확률이 아닌 기술적 적합도 점수이며, 투자 결정의 책임은 본인에게 있습니다.
</div>

</div>
</div>
</div>
""", unsafe_allow_html=True)

        st.info("👈 사이드바에서 종목명 또는 티커를 입력하고 **분석 실행**을 눌러주세요.")

        if 'quick_ticker' in st.session_state:
            st.info(f"💡 사이드바에서 **{st.session_state.get('quick_name', '')}** 을 검색하고 분석 실행을 눌러주세요.")

        # ── 보유종목 리스트 (첫화면 하단) ─────────────────────
        if 'portfolio' in st.session_state and st.session_state.portfolio:
            st.divider()
            st.markdown('<div class="sec-hdr">💼 보유종목 현황</div>', unsafe_allow_html=True)

            col_ref, _ = st.columns([1, 5])
            with col_ref:
                if st.button("🔄 현재가 + 점수 갱신", key="home_refresh"):
                    for pos in st.session_state.portfolio:
                        try:
                            df_p = fetch(pos['ticker'], days=300)
                            if len(df_p) >= 130:
                                pos['curr_price'] = float(df_p['Close'].iloc[-1])
                                pos['curr_date']  = df_p.index[-1].strftime('%m/%d')
                                d_p  = compute(df_p)
                                row_p = d_p.iloc[-1]
                                g_raw_p, _ = g_score(row_p)
                                f1_ok_p, _ = check_f1()
                                sc_p = calc_scores(g_raw_p, f1_ok_p, pos['avg_price'],
                                                   pos['curr_price'],
                                                   float(row_p['atr']) if not pd.isna(row_p['atr']) else 0)
                                pos['buy_pct']  = sc_p['buy']
                                pos['hold_pct'] = sc_p['hold']
                                pos['sell_pct'] = sc_p['sell']
                        except:
                            pass
                    st.rerun()

            st.markdown("""
            <div style="display:grid;
                grid-template-columns:110px 80px 80px 70px 80px 80px 60px 60px 60px;
                gap:4px;padding:6px 10px;background:#0f1623;border-radius:6px;
                font-size:0.67rem;letter-spacing:0.08em;text-transform:uppercase;
                color:#475569;font-weight:600;margin-bottom:4px">
                <div>종목명</div>
                <div style="text-align:right">매수가</div>
                <div style="text-align:right">현재가</div>
                <div style="text-align:right">수익률</div>
                <div style="text-align:right">목표가</div>
                <div style="text-align:right">손절가</div>
                <div style="text-align:center">매수%</div>
                <div style="text-align:center">홀딩%</div>
                <div style="text-align:center">매도%</div>
            </div>""", unsafe_allow_html=True)

            for pos in st.session_state.portfolio:
                pnl_pct  = (pos['curr_price'] / pos['avg_price'] - 1) * 100
                sl_price = pos['avg_price'] * 0.92
                tp_price = pos['avg_price'] * 1.15
                is_sl    = pos['curr_price'] <= sl_price

                buy_s  = pos.get('buy_pct',  None)
                hold_s = pos.get('hold_pct', None)
                sell_s = pos.get('sell_pct', None)

                row_bg = '#1a0a0a' if is_sl else ('#0f2d1a' if pnl_pct >= 15 else ('#0a150f' if pnl_pct >= 0 else '#150a0a'))
                row_bd = '#ef4444' if is_sl else ('#166534' if pnl_pct >= 15 else '#1e2a3a')
                pnl_color = '#22c55e' if pnl_pct >= 0 else '#ef4444'
                buy_color  = '#22c55e' if buy_s and buy_s >= 50 else '#94a3b8'
                sell_color = '#ef4444' if sell_s and sell_s >= 50 else '#94a3b8'

                buy_disp  = f"{buy_s}%"  if buy_s  is not None else '—'
                hold_disp = f"{hold_s}%" if hold_s is not None else '—'
                sell_disp = f"{sell_s}%" if sell_s is not None else '—'

                sl_warn = ' ⚠️' if is_sl else ''
                curr_str = f"${pos['curr_price']:,.2f}"
                avg_str  = f"${pos['avg_price']:,.2f}"

                st.markdown(f"""
                <div style="display:grid;
                    grid-template-columns:110px 80px 80px 70px 80px 80px 60px 60px 60px;
                    gap:4px;padding:8px 10px;background:{row_bg};
                    border:1px solid {row_bd};border-radius:6px;margin-bottom:3px;
                    align-items:center;font-family:Space Mono,monospace;font-size:0.79rem">
                    <div style="font-family:Space Grotesk,sans-serif;font-weight:600;color:#e2e8f0">
                        {pos['name']}<span style="color:#ef4444">{sl_warn}</span></div>
                    <div style="text-align:right;color:#64748b">{avg_str}</div>
                    <div style="text-align:right;color:#e2e8f0;font-weight:600">{curr_str}</div>
                    <div style="text-align:right;color:{pnl_color};font-weight:700">{pnl_pct:+.1f}%</div>
                    <div style="text-align:right;color:#22c55e">${tp_price:,.2f}</div>
                    <div style="text-align:right;color:#ef4444">${sl_price:,.2f}</div>
                    <div style="text-align:center;color:{buy_color};font-weight:700">{buy_disp}</div>
                    <div style="text-align:center;color:#eab308">{hold_disp}</div>
                    <div style="text-align:center;color:{sell_color}">{sell_disp}</div>
                </div>
                """, unsafe_allow_html=True)

                if is_sl:
                    st.markdown('<div class="verdict-banner verdict-sell">⚠️ 손절선 이탈 — 즉시 매도 또는 포지션 재검토</div>', unsafe_allow_html=True)

            st.markdown(
                "<div style='font-size:0.72rem;color:#334155;margin-top:4px'>"
                "💡 점수 표시는 갱신 버튼 클릭 시 업데이트됩니다.</div>",
                unsafe_allow_html=True
            )

        # ── 보유종목 관리 탭 (항상 표시) ───────────────────
        st.divider()
        st.markdown('<div class="sec-hdr">💼 보유종목 추가/관리</div>', unsafe_allow_html=True)
        _render_portfolio_tab()
        return

    # 데이터 로딩
    # ★ 돋보기 분석 세션 정리
    st.session_state.pop('analyze_ticker', None)
    st.session_state.pop('analyze_name', None)

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

    # G 점수 + 유니버스 백분위 계산 (3자 합의: 백테스트와 동일한 상대순위)
    g_raw, g_detail = g_score(row)

    # 유니버스 판별 (KS = 국내, 나머지 = 미국)
    market = 'KR' if ticker.endswith('.KS') or ticker.endswith('.KQ') else 'US'

    # 유니버스 스캔으로 실제 백분위 계산
    with st.spinner(f"유니버스 백분위 계산 중 ({"국내" if market=="KR" else "미국"} {"62" if market=="KR" else "155"}종목)..."):
        df_universe = scan_market(market)

    universe_pct  = 50.0   # 기본값
    universe_rank = None
    universe_total = None

    if not df_universe.empty:
        # 전체 유니버스 G 원점수 중 해당 종목 위치 계산
        all_g_scores = df_universe['g_raw'].values
        universe_pct  = float((all_g_scores < g_raw).sum() / len(all_g_scores) * 100)
        universe_rank = int((all_g_scores >= g_raw).sum())
        universe_total = len(all_g_scores)

    scores = calc_scores(g_raw, f1_ok, avg_price if has_pos else None, close, atr,
                         universe_pct=universe_pct)

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

    # ── F1 필터 대시보드 (Gemini 제안 반영) ───────────────────
    f1_color     = '#166534' if f1_ok else '#92400e'
    f1_bg        = '#0f2d1a' if f1_ok else '#2d1a00'
    f1_icon      = '✅' if f1_ok else '⚠️'
    f1_status    = 'OFF — 매수 신호 활성' if f1_ok else 'ON — 신규 매수 비활성화'
    f1_bar_pct   = min(100, abs(tnx_change) / 0.75 * 100) if not np.isnan(tnx_change) else 0
    f1_bar_color = '#22c55e' if f1_ok else '#ef4444'
    f1_tnx_str   = f'{tnx_change:+.2f}%p' if not np.isnan(tnx_change) else 'N/A'
    f1_remain    = (f'+{0.75 - tnx_change:.2f}%p 여유' if f1_ok and not np.isnan(tnx_change)
                    else (f'{tnx_change:+.2f}%p — 임계값 초과' if not f1_ok else '데이터 확인 중'))

    st.markdown(f"""
    <div style='background:{f1_bg};border:1px solid {f1_color};border-radius:10px;
        padding:0.8rem 1.2rem;margin-bottom:1rem'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px'>
            <span style='font-weight:600;color:#e2e8f0;font-size:0.92rem'>
                {f1_icon} 금리충격 필터 (F1) &nbsp;{f1_status}
            </span>
            <span style='font-family:Space Mono,monospace;font-size:0.78rem;color:#94a3b8'>
                10Y금리 60일 변화 {f1_tnx_str} / 임계값 +0.75%p
            </span>
        </div>
        <div style='background:#1e2a3a;border-radius:4px;height:5px;overflow:hidden'>
            <div style='background:{f1_bar_color};width:{f1_bar_pct:.0f}%;height:5px;border-radius:4px'></div>
        </div>
        <div style='font-size:0.72rem;color:#64748b;margin-top:4px'>{f1_remain}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 유니버스 순위 배너 ────────────────────────────────
    if universe_rank is not None:
        rank_pct  = round(universe_pct, 1)
        rank_color = '#22c55e' if rank_pct >= 80 else ('#eab308' if rank_pct >= 60 else '#ef4444')
        tier = ('강한 매수 후보 (상위 10%)' if rank_pct >= 90 else
                '매수 후보 (상위 20%)' if rank_pct >= 80 else
                '보유 가능 (상위 40%)' if rank_pct >= 60 else
                '신규매수 부적합')
        market_label = '국내' if market == 'KR' else '미국'
        st.markdown(f"""
        <div style='background:#0f1623;border:1px solid #1e2a3a;border-radius:8px;
            padding:0.7rem 1.2rem;margin-bottom:0.8rem;
            display:flex;justify-content:space-between;align-items:center'>
            <span style='font-size:0.85rem;color:#94a3b8'>
                {market_label} {universe_total}종목 유니버스 내 순위
            </span>
            <span>
                <span style='font-family:Space Mono,monospace;font-size:1.1rem;
                    font-weight:700;color:{rank_color}'>{universe_rank}위</span>
                <span style='color:#475569;font-size:0.8rem'> / {universe_total}종목</span>
                <span style='margin-left:10px;background:#1e2a3a;padding:2px 8px;
                    border-radius:12px;font-size:0.78rem;color:{rank_color}'>{tier}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── 점수 카드 ─────────────────────────────────────────
    st.markdown(f"""
    <div class="score-wrap">
        <div class="score-card card-buy">
            <div class="score-label">매수 적합도</div>
            <div class="score-num-buy">{scores['buy']}%</div>
            <div class="score-sub">유니버스 백분위 {round(universe_pct,1)}%</div>
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 차트", "🔢 신호 상세", "🛡️ 손절 관리", "🔍 전종목 스캐너", "🚨 매수 알람", "💼 보유종목 관리"])

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
        n_us = len(SCAN_US)
        n_kr = len(SCAN_KR)
        st.markdown(
            f"<div style='font-size:0.82rem;color:#475569;margin-bottom:1rem'>"
            f"G_US_F1 신호 기반 전종목 스캔 — "
            f"🇺🇸 미국 <b style='color:#e2e8f0'>{n_us}종목</b> / "
            f"🇰🇷 국내 <b style='color:#e2e8f0'>{n_kr}종목</b> · 매 10분 캐시 갱신</div>",
            unsafe_allow_html=True
        )

        # 필터 옵션
        sf1, sf2, sf3 = st.columns(3)
        with sf1:
            threshold = st.slider("매수 적합도 하한", 0, 80, 50, 5,
                                   help="이 값 이상인 종목만 표시")
        with sf2:
            show_all = st.toggle("전체 종목 보기", value=False,
                                  help="OFF: 매수 우위만 / ON: 전체")
        with sf3:
            sort_by = st.selectbox("정렬 기준", ["매수% 높은순", "매도% 높은순", "RSI 낮은순"])

        sc_col1, sc_col2 = st.columns(2)

        for col_, market_, label_ in [(sc_col1,'US','🇺🇸 미국주식'), (sc_col2,'KR','🇰🇷 국내주식')]:
            with col_:
                n_total = len(SCAN_US) if market_ == 'US' else len(SCAN_KR)
                st.markdown(f"**{label_}** ({n_total}종목)")
                with st.spinner(f"{label_} 스캔 중... ({n_total}종목, 약 1~2분 소요)"):
                    df_scan = scan_market(market_)

                if df_scan.empty:
                    st.warning("데이터를 가져오지 못했습니다.")
                    continue

                # 정렬
                if sort_by == "매도% 높은순":
                    df_scan = df_scan.sort_values('sell_pct', ascending=False)
                elif sort_by == "RSI 낮은순":
                    df_scan = df_scan.sort_values('rsi', ascending=True)

                # 필터
                if not show_all:
                    df_view = df_scan[df_scan['buy_pct'] >= threshold]
                else:
                    df_view = df_scan

                # 매수 우위 하이라이트
                top_picks = df_scan[df_scan['buy_pct'] >= 60]
                n_pass = len(top_picks)
                n_total_scanned = len(df_scan)

                st.markdown(
                    f"<div style='display:flex;gap:12px;margin-bottom:0.8rem'>",
                    unsafe_allow_html=True
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("스캔 완료", f"{n_total_scanned}종목")
                with col_b:
                    st.metric("매수 우위 (60%↑)", f"{n_pass}종목")
                with col_c:
                    st.metric("표시 중", f"{len(df_view)}종목")

                if not top_picks.empty:
                    names = ', '.join(top_picks['name'].tolist())
                    st.markdown(
                        f"<div style='background:#0f2d1a;border:1px solid #166534;"
                        f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.8rem;"
                        f"font-size:0.82rem;color:#86efac'>"
                        f"🎯 매수 우위 종목: <b>{names}</b></div>",
                        unsafe_allow_html=True
                    )

                # 순위표 렌더링
                for _, r in df_view.iterrows():
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
                                <span style="font-size:0.7rem;padding:1px 6px;border-radius:10px;
                                    background:#1e2a3a;color:#64748b;margin-left:4px">
                                    유니버스 {r['rank']}위/{r['total']}
                                </span>
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



    # ── 탭5: 매수 알람 ─────────────────────────────────────
    with tab5:
        st.markdown('<div class="sec-hdr">매수 알람 — 매수 점수 90% 이상 종목</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.82rem;color:#475569;margin-bottom:1rem'>"
            "G_US_F1 유니버스 백분위 기준 — <b style='color:#22c55e'>상위 20% (매수 후보)</b> 이상 종목 표시 · "
            "종목 클릭 시 차트 표시 · 매 10분 캐시 갱신</div>",
            unsafe_allow_html=True
        )

        # 스캔 실행
        alarm_col1, alarm_col2 = st.columns(2)

        alarm_results = {}
        for market_, label_ in [('US','🇺🇸 미국주식'), ('KR','🇰🇷 국내주식')]:
            with st.spinner(f"{label_} 스캔 중..."):
                df_s = scan_market(market_)
            if not df_s.empty:
                alarm_results[market_] = df_s

        # 임계값 선택
        alarm_thresh = st.slider(
            "매수 점수 기준", 50, 95, 70, 5,
            help="이 값 이상인 종목만 알람 목록에 표시합니다",
            key="alarm_thresh"
        )

        for market_, label_ in [('US','🇺🇸 미국주식'), ('KR','🇰🇷 국내주식')]:
            st.markdown(f"### {label_}")

            if market_ not in alarm_results or alarm_results[market_].empty:
                st.warning("데이터 없음")
                continue

            df_alarm = alarm_results[market_][
                alarm_results[market_]['buy_pct'] >= alarm_thresh
            ].copy().reset_index(drop=True)

            if df_alarm.empty:
                st.info(f"현재 매수 점수 {alarm_thresh}% 이상 종목이 없습니다.")
                continue

            # 통계 요약
            st.markdown(
                f"<div style='background:#0f2d1a;border:1px solid #166534;"
                f"border-radius:8px;padding:0.6rem 1rem;margin-bottom:0.8rem;"
                f"font-size:0.85rem;color:#86efac'>"
                f"🎯 {len(df_alarm)}개 종목 감지 (전체 "
                f"{'미국 155' if market_=='US' else '국내 62'}종목 중)</div>",
                unsafe_allow_html=True
            )

            # 테이블 헤더
            st.markdown("""
            <div style="display:grid;grid-template-columns:80px 120px 130px 90px 90px 90px;
                gap:4px;padding:6px 8px;background:#0f1623;border-radius:6px;
                font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;
                color:#475569;font-weight:600;margin-bottom:4px">
                <div>티커</div><div>종목명</div>
                <div>현재가 (날짜)</div>
                <div style="text-align:center">매수</div>
                <div style="text-align:center">홀딩</div>
                <div style="text-align:center">매도</div>
            </div>""", unsafe_allow_html=True)

            # 종목 행 렌더링
            selected_ticker = None
            selected_name   = None

            for idx_, r in df_alarm.iterrows():
                buy_  = r['buy_pct']
                hold_ = r['hold_pct']
                sell_ = r['sell_pct']

                # 매수 점수별 강도 색상
                if buy_ >= 80:
                    buy_color = '#22c55e'
                    row_bg    = '#0a1a0f'
                    row_bdr   = '#166534'
                elif buy_ >= 70:
                    buy_color = '#86efac'
                    row_bg    = '#0a150f'
                    row_bdr   = '#14532d'
                else:
                    buy_color = '#bbf7d0'
                    row_bg    = '#0f1623'
                    row_bdr   = '#1e2a3a'

                # 날짜 (오늘 기준)
                from datetime import date
                today_str = date.today().strftime('%m/%d')

                row_html = f"""
                <div style="display:grid;grid-template-columns:80px 120px 130px 90px 90px 90px;
                    gap:4px;padding:8px 8px;background:{row_bg};
                    border:1px solid {row_bdr};border-radius:6px;
                    margin-bottom:3px;align-items:center">
                    <div style="font-family:Space Mono,monospace;font-size:0.8rem;
                        color:#94a3b8">{r['ticker']}</div>
                    <div style="font-size:0.88rem;font-weight:600;
                        color:#e2e8f0">{r['name']}</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;color:#64748b">
                        ${r['close']:,.2f}
                        <span style="font-size:0.7rem;color:#334155"> {today_str}</span>
                    </div>
                    <div style="text-align:center;font-family:Space Mono,monospace;
                        font-weight:700;font-size:0.9rem;color:{buy_color}">{buy_}%</div>
                    <div style="text-align:center;font-family:Space Mono,monospace;
                        font-size:0.85rem;color:#eab308">{hold_}%</div>
                    <div style="text-align:center;font-family:Space Mono,monospace;
                        font-size:0.85rem;color:#ef4444">{sell_}%</div>
                </div>"""
                st.markdown(row_html, unsafe_allow_html=True)

                # 클릭 버튼 (차트 토글)
                btn_key = f"alarm_btn_{market_}_{r['ticker']}"
                if st.button(f"📈 {r['name']} 차트 보기", key=btn_key,
                              use_container_width=False):
                    st.session_state[f'alarm_chart_{market_}'] = r['ticker']
                    st.session_state[f'alarm_chart_{market_}_name'] = r['name']

            # 선택된 종목 차트 표시
            chart_key = f'alarm_chart_{market_}'
            if chart_key in st.session_state:
                sel_ticker = st.session_state[chart_key]
                sel_name   = st.session_state.get(f'{chart_key}_name', sel_ticker)
                st.markdown(f"---")
                st.markdown(f"**📈 {sel_name} ({sel_ticker}) 차트**")
                with st.spinner(f"{sel_ticker} 차트 로딩 중..."):
                    try:
                        df_chart = fetch(sel_ticker)
                        if len(df_chart) >= 130:
                            fig_alarm = make_chart(df_chart, sel_ticker)
                            st.plotly_chart(fig_alarm, use_container_width=True)

                            # 간단 신호 요약
                            d_alarm  = compute(df_chart)
                            row_alarm = d_alarm.iloc[-1]
                            g_raw_a, _ = g_score(row_alarm)
                            f1_ok_a, _ = check_f1()
                            sc_a = calc_scores(g_raw_a, f1_ok_a, None,
                                               float(row_alarm['Close']),
                                               float(row_alarm['atr']) if not pd.isna(row_alarm['atr']) else 0)
                            v = sc_a['verdict']
                            cls_map2 = {'buy':'verdict-buy','hold':'verdict-hold',
                                        'sell':'verdict-sell','filter':'verdict-filter'}
                            st.markdown(
                                f'<div class="verdict-banner {cls_map2[v]}">'
                                f'{sc_a["verdict_text"]}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning("데이터 부족")
                    except Exception as e:
                        st.error(f"차트 로딩 실패: {e}")

            st.markdown("<br>", unsafe_allow_html=True)



    # ── 탭6: 보유종목 관리 ────────────────────────────────
    with tab6:
        _render_portfolio_tab()

    # 면책 고지
    st.markdown("""
    <div class="disclaimer">
    ⚠️ <b>투자 유의사항:</b> 이 앱의 점수는 G_US_F1 백테스트(2010~2025) 기반 기술적 적합도 점수이며,
    실제 수익률을 보장하지 않습니다. 과거 성과(CAGR +9.3%, MDD -26.0%)는 미래 성과를 보장하지 않으며,
    개별 종목 결과는 포트폴리오 전체 백테스트 결과와 다를 수 있습니다.
    투자 결정의 최종 책임은 본인에게 있습니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
