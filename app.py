import streamlit as st
import requests
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V47 INSTITUTIONAL AI", layout="wide")

st.title("🏛️ V47 INSTITUTIONAL AI ENGINE")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh Market"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK MODE
# =========================
st.markdown("""
<style>

.stApp {
    background:#05070D;
    color:#EAEAEA;
}

h1,h2,h3 {
    color:#00E5FF;
}

.card {
    background:#0B1220;
    padding:14px;
    border-radius:14px;
    margin-bottom:12px;
    border:1px solid #1f2937;
}

.buy { border-left:5px solid #00FF88; }
.sell { border-left:5px solid #FF3B3B; }

.low { opacity:0.5; }
.med { opacity:0.8; }
.high { opacity:1; }

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA
# =========================
@st.cache_data(ttl=30)
def load_data(symbol):

    if not API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "values" not in r:
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# =========================
# MARKET REGIME DETECTION (NEW CORE)
# =========================
def regime(df):

    returns = df["close"].pct_change()
    volatility = returns.std()
    trend = returns.mean()

    if volatility > 0.004:
        return "VOLATILE"
    elif abs(trend) > 0.0008:
        return "TREND"
    else:
        return "RANGE"

# =========================
# STRUCTURE
# =========================
def structure(df):

    price = df["close"].iloc[-1]

    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]

    atr = (df["high"] - df["low"]).rolling(20).mean().iloc[-1]

    momentum = df["close"].diff(5).iloc[-1]

    return price, support, resistance, atr, momentum

# =========================
# V47 ENGINE
# =========================
def engine(price, support, resistance, atr, momentum, regime_state):

    rng = resistance - support

    score = 50
    reasons = []

    # =========================
    # REGIME FILTER (VERY IMPORTANT)
    # =========================
    if regime_state == "TREND":
        score += 15
        reasons.append("Trend regime detected")

    elif regime_state == "VOLATILE":
        score -= 10
        reasons.append("High volatility risk")

    else:
        reasons.append("Range market")

    # =========================
    # MOMENTUM
    # =========================
    if momentum > 0:
        score += 10
        reasons.append("Positive momentum")
        direction_bias = "BUY"
    else:
        score -= 10
        reasons.append("Negative momentum")
        direction_bias = "SELL"

    # =========================
    # STRUCTURE
    # =========================
    breakout = price > resistance * 0.999
    breakdown = price < support * 1.001

    near_support = price <= support * 1.002
    near_resistance = price >= resistance * 0.998

    # =========================
    # SIGNAL QUALITY FILTER (NEW)
    # =========================
    quality_gate = 0

    if regime_state == "VOLATILE":
        quality_gate = 1
    elif regime_state == "TREND":
        quality_gate = 2
    else:
        quality_gate = 3

    # =========================
    # SIGNAL LOGIC
    # =========================
    if breakout and quality_gate >= 2:
        signal = "INSTITUTIONAL BUY"
        direction = "BUY"
        entry = resistance
        sl = support
        tp = resistance + rng
        score += 25
        reasons.append("High quality breakout")

    elif breakdown and quality_gate >= 2:
        signal = "INSTITUTIONAL SELL"
        direction = "SELL"
        entry = support
        sl = resistance
        tp = support - rng
        score += 25
        reasons.append("High quality breakdown")

    elif near_support and regime_state != "VOLATILE":
        signal = "ACCUMULATION BUY"
        direction = "BUY"
        entry = support
        sl = support - atr
        tp = resistance
        score += 15
        reasons.append("Institutional accumulation zone")

    elif near_resistance and regime_state != "VOLATILE":
        signal = "DISTRIBUTION SELL"
        direction = "SELL"
        entry = resistance
        sl = resistance + atr
        tp = support
        score += 15
        reasons.append("Institutional distribution zone")

    else:
        signal = "NO INSTITUTIONAL EDGE"
        direction = "WAIT"
        entry = price
        sl = price - atr
        tp = price + atr
        score -= 8
        reasons.append("No edge condition")

    # =========================
    # RISK / RR FILTER
    # =========================
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    if rr >= 2:
        score += 12
    elif rr < 1.2:
        score -= 10

    score = max(0, min(100, score))

    return signal, direction, entry, sl, tp, rr, score, reasons

# =========================
# RUN SCAN
# =========================
results = []

for coin in selected:

    df = load_data(coin)

    if df is None or df.empty:
        continue

    price, support, resistance, atr, momentum = structure(df)
    regime_state = regime(df)

    signal, direction, entry, sl, tp, rr, score, reasons = engine(
        price, support, resistance, atr, momentum, regime_state
    )

    results.append({
        "Coin": coin,
        "Regime": regime_state,
        "Signal": signal,
        "Direction": direction,
        "Score": score,
        "RR": rr,
        "Reasons": reasons
    })

df = pd.DataFrame(results).sort_values("Score", ascending=False)

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("🟢 BUY", len(df[df["Direction"] == "BUY"]))
c2.metric("🔴 SELL", len(df[df["Direction"] == "SELL"]))
c3.metric("🔥 TOP SCORE", df["Score"].max())

# =========================
# INSTITUTIONAL RANKING
# =========================
st.subheader("🏛️ INSTITUTIONAL MARKET VIEW (V47)")

for i, r in df.iterrows():

    cls = "buy" if r["Direction"] == "BUY" else "sell"

    st.markdown(f"""
    <div class="card {cls}">

    <h3>{r['Coin']} – {r['Direction']}</h3>

    📊 Regime: {r['Regime']}<br>
    🧠 Signal: {r['Signal']}<br>

    <hr>

    📊 RR: {r['RR']}<br>
    🧠 Score: {r['Score']}

    <hr>

    🧠 AI REASONS:<br>
    {"<br>".join(["- " + x for x in r["Reasons"]])}

    </div>
    """, unsafe_allow_html=True)
