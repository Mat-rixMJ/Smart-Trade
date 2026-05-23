"""
public_dashboard.py — Algodhan Performance Viewer
===================================================
Read-only, presentation-grade analytics dashboard.
Designed for resume showcase, recruiter demos, and live audience viewing.
No controls, no logs, no sensitive data — pure data visualization.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import time
import json
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
from dotenv import load_dotenv
from config import CAPITAL
from holidays import is_market_holiday

load_dotenv()

# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Algodhan — Quantitative Performance Analytics",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════
#  PREMIUM CSS THEME (Glassmorphism + Outfit Font)
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    font-family: 'Outfit', sans-serif;
    background: #08080c;
    color: #e2e8f0;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { display: none; }

/* Glassmorphic metric cards */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.025);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 16px 48px rgba(99, 102, 241, 0.12);
}

[data-testid="stMetricLabel"] { font-weight: 500; letter-spacing: 0.02em; }
[data-testid="stMetricValue"] { font-weight: 700; }

/* Header gradient */
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 40%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 2px;
    letter-spacing: -0.02em;
}

.hero-sub {
    color: #64748b;
    font-size: 1.05rem;
    margin-bottom: 32px;
    font-weight: 400;
}

/* Section headers */
.section-header {
    font-size: 1.3rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Position cards */
.pos-card-win {
    background: rgba(16, 185, 129, 0.06);
    border: 1px solid rgba(16, 185, 129, 0.2);
    padding: 14px 18px;
    border-radius: 14px;
    margin-bottom: 10px;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.06);
}

.pos-card-loss {
    background: rgba(255, 255, 255, 0.015);
    border: 1px solid rgba(255, 255, 255, 0.04);
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 8px;
    opacity: 0.55;
}

.pos-card-open {
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.2);
    padding: 14px 18px;
    border-radius: 14px;
    margin-bottom: 10px;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.06);
}

.no-pos {
    background: rgba(255, 255, 255, 0.015);
    border: 1px dashed rgba(255, 255, 255, 0.08);
    padding: 28px;
    border-radius: 14px;
    text-align: center;
    color: #64748b;
}

/* Footer */
.footer {
    text-align: center;
    color: #475569;
    font-size: 0.8rem;
    margin-top: 40px;
    padding: 20px 0;
    border-top: 1px solid rgba(255,255,255,0.04);
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PLOTLY THEME DEFAULTS
# ══════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#94a3b8", size=13),
    margin=dict(l=40, r=20, t=40, b=40),
    hoverlabel=dict(bgcolor="#1e1e2e", font_color="#e2e8f0", bordercolor="rgba(99,102,241,0.3)"),
)

# ══════════════════════════════════════════════════════════════
#  DATA ENGINE
# ══════════════════════════════════════════════════════════════
DB_PATH = "logs/trades.db"
STATE_FILE = "logs/system_state.json"

@st.cache_data(ttl=8)
def load_all_data():
    """Load and compute all analytics from the trade database."""
    default_stats = {
        "today_pnl": 0.0, "total_pnl": 0.0, "today_count": 0, "win_rate": 0.0,
        "total_trades": 0, "all_time_win_rate": 0.0, "sharpe_ratio": 0.0,
        "max_dd": 0.0, "profit_factor": 1.0, "avg_win": 0.0, "avg_loss": 0.0,
        "best_trade": 0.0, "worst_trade": 0.0, "expectancy": 0.0,
        "avg_rr": 0.0, "consecutive_wins": 0, "consecutive_losses": 0,
        "total_capital": 0.0
    }
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(), default_stats

    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.execute("PRAGMA busy_timeout = 3000;")
        df = pd.read_sql("SELECT * FROM trades", conn)
    except Exception as e:
        import sys
        print(f"Error loading trade data: {e}", file=sys.stderr)
        return pd.DataFrame(), default_stats
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if df.empty:
        return df, default_stats

    closed = df[df['status'] == 'CLOSED'].copy()
    total_pnl = float(closed['pnl'].sum())
    total_trades = len(closed)
    total_cap = float(CAPITAL.get("total", 5000.0))

    # Today
    today_str = date.today().isoformat()
    today_trades = closed[closed['date'] == today_str]
    today_pnl = float(today_trades['pnl'].sum())
    today_count = len(today_trades)
    today_wins = len(today_trades[today_trades['pnl'] > 0])
    win_rate = (today_wins / today_count * 100) if today_count > 0 else 0.0

    # All-time
    all_wins = len(closed[closed['pnl'] > 0])
    all_time_win_rate = (all_wins / total_trades * 100) if total_trades > 0 else 0.0

    # Win/Loss averages
    wins_df = closed[closed['pnl'] > 0]
    loss_df = closed[closed['pnl'] < 0]
    avg_win = float(wins_df['pnl'].mean()) if not wins_df.empty else 0.0
    avg_loss = float(loss_df['pnl'].mean()) if not loss_df.empty else 0.0
    best_trade = float(closed['pnl'].max()) if not closed.empty else 0.0
    worst_trade = float(closed['pnl'].min()) if not closed.empty else 0.0

    # Expectancy
    if total_trades > 0:
        expectancy = (all_time_win_rate / 100 * avg_win) + ((1 - all_time_win_rate / 100) * avg_loss)
    else:
        expectancy = 0.0

    # Avg RR
    if avg_loss != 0:
        avg_rr = abs(avg_win / avg_loss)
    else:
        avg_rr = 0.0

    # Consecutive wins / losses
    consec_w, consec_l, cw, cl = 0, 0, 0, 0
    for p in closed['pnl'].tolist():
        if p > 0:
            cw += 1
            cl = 0
        else:
            cl += 1
            cw = 0
        consec_w = max(consec_w, cw)
        consec_l = max(consec_l, cl)

    # Sharpe Ratio
    pnl_series = closed['pnl'].astype(float).tolist()
    if len(pnl_series) > 1:
        returns = np.array(pnl_series) / total_cap
        std = returns.std()
        mean_ret = returns.mean()
        sharpe_ratio = (mean_ret / std * np.sqrt(252 * 5)) if std > 0 else 0.0
    else:
        sharpe_ratio = 0.0

    # Max Drawdown
    equity = [total_cap]
    for p in pnl_series:
        equity.append(equity[-1] + p)
    equity_s = pd.Series(equity)
    cum_max = equity_s.cummax()
    drawdowns = (equity_s - cum_max) / cum_max * 100
    max_dd = float(drawdowns.min())

    # Profit Factor
    gross_wins = float(wins_df['pnl'].sum()) if not wins_df.empty else 0.0
    gross_losses = float(abs(loss_df['pnl'].sum())) if not loss_df.empty else 0.0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else (float('inf') if gross_wins > 0 else 1.0)

    final_capital = total_cap + total_pnl

    stats = {
        "today_pnl": today_pnl, "total_pnl": total_pnl,
        "today_count": today_count, "win_rate": win_rate,
        "total_trades": total_trades, "all_time_win_rate": all_time_win_rate,
        "sharpe_ratio": sharpe_ratio, "max_dd": max_dd, "profit_factor": profit_factor,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "best_trade": best_trade, "worst_trade": worst_trade,
        "expectancy": expectancy, "avg_rr": avg_rr,
        "consecutive_wins": consec_w, "consecutive_losses": consec_l,
        "total_capital": final_capital,
    }
    return df, stats


def build_equity_chart(df, total_cap):
    """Build Plotly equity curve with drawdown underlay."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    closed['datetime'] = pd.to_datetime(closed['date'] + ' ' + closed['time'])
    closed = closed.sort_values('datetime')

    equity = [total_cap]
    for p in closed['pnl'].astype(float):
        equity.append(equity[-1] + p)
    timestamps = [closed['datetime'].iloc[0] - pd.Timedelta(minutes=5)] + closed['datetime'].tolist()

    # Drawdown series
    eq_s = pd.Series(equity)
    peak = eq_s.cummax()
    dd_pct = (eq_s - peak) / peak * 100

    fig = go.Figure()

    # Drawdown fill (subtle red underlay)
    fig.add_trace(go.Scatter(
        x=timestamps, y=dd_pct, name="Drawdown %",
        fill='tozeroy', fillcolor='rgba(239,68,68,0.08)',
        line=dict(color='rgba(239,68,68,0.3)', width=1),
        yaxis='y2', hovertemplate='Drawdown: %{y:.2f}%<extra></extra>'
    ))

    # Equity line (gradient feel via color)
    fig.add_trace(go.Scatter(
        x=timestamps, y=equity, name="Portfolio Equity",
        line=dict(color='#6366f1', width=2.5, shape='spline'),
        fill='tozeroy', fillcolor='rgba(99,102,241,0.06)',
        hovertemplate='₹%{y:,.2f}<extra></extra>'
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#94a3b8", size=13),
        margin=dict(l=40, r=40, t=40, b=40),
        hoverlabel=dict(bgcolor="#1e1e2e", font_color="#e2e8f0", bordercolor="rgba(99,102,241,0.3)"),
        height=380,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Equity (₹)", gridcolor="rgba(255,255,255,0.04)", side='left'),
        yaxis2=dict(title="Drawdown %", overlaying='y', side='right',
                    gridcolor="rgba(255,255,255,0.02)", range=[min(dd_pct) * 1.5, 5]),
    )
    return fig


def build_daily_pnl_chart(df):
    """Daily P&L waterfall bar chart."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    daily = closed.groupby('date')['pnl'].sum().reset_index()
    daily.columns = ['Date', 'P&L']
    daily['Color'] = daily['P&L'].apply(lambda x: '#10b981' if x >= 0 else '#ef4444')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily['Date'], y=daily['P&L'],
        marker_color=daily['Color'],
        marker_line_width=0,
        hovertemplate='%{x}<br>P&L: ₹%{y:,.2f}<extra></extra>',
        opacity=0.85
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        xaxis=dict(title="", tickangle=-45, dtick="M1", tickformat="%b %Y", gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(title="Daily P&L (₹)", gridcolor="rgba(255,255,255,0.04)"),
        bargap=0.15,
    )
    return fig


def build_monthly_returns_heatmap(df):
    """Monthly returns heatmap."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    closed['date_parsed'] = pd.to_datetime(closed['date'])
    closed['month'] = closed['date_parsed'].dt.month
    closed['year'] = closed['date_parsed'].dt.year

    monthly = closed.groupby(['year', 'month'])['pnl'].sum().reset_index()
    total_cap = float(CAPITAL.get("total", 5000.0))
    monthly['return_pct'] = (monthly['pnl'] / total_cap) * 100

    pivot = monthly.pivot(index='year', columns='month', values='return_pct').fillna(0)
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    # Reindex columns to ensure all 12 months present
    pivot = pivot.reindex(columns=range(1, 13), fill_value=0)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[month_names[i] for i in range(12)],
        y=[str(y) for y in pivot.index],
        colorscale=[[0, '#ef4444'], [0.5, '#1e1e2e'], [1, '#10b981']],
        zmid=0,
        hovertemplate='%{y} %{x}<br>Return: %{z:.2f}%<extra></extra>',
        colorbar=dict(title="Return %", ticksuffix="%"),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
        yaxis=dict(autorange='reversed'),
    )
    return fig


def build_symbol_performance(df):
    """Horizontal bar chart of P&L by symbol."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    sym_pnl = closed.groupby('symbol')['pnl'].sum().sort_values()
    colors = ['#10b981' if v >= 0 else '#ef4444' for v in sym_pnl.values]

    fig = go.Figure(go.Bar(
        x=sym_pnl.values, y=sym_pnl.index,
        orientation='h',
        marker_color=colors,
        marker_line_width=0,
        hovertemplate='%{y}<br>Total P&L: ₹%{x:,.2f}<extra></extra>',
        opacity=0.85
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=350,
        xaxis=dict(title="Cumulative P&L (₹)", gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(title=""),
        bargap=0.2,
    )
    return fig


def build_win_loss_donut(df):
    """Win/Loss/Breakeven donut chart."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    wins = len(closed[closed['pnl'] > 0])
    losses = len(closed[closed['pnl'] < 0])
    be = len(closed[closed['pnl'] == 0])

    fig = go.Figure(go.Pie(
        labels=['Wins', 'Losses', 'Breakeven'],
        values=[wins, losses, be],
        hole=0.6,
        marker=dict(colors=['#10b981', '#ef4444', '#6366f1'],
                    line=dict(color='#08080c', width=3)),
        textinfo='label+percent',
        textfont=dict(color='#e2e8f0', size=13),
        hovertemplate='%{label}: %{value} trades (%{percent})<extra></extra>',
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        showlegend=False,
        annotations=[dict(text=f"{wins + losses + be}<br>Trades", x=0.5, y=0.5,
                          font_size=16, font_color="#e2e8f0", showarrow=False)],
    )
    return fig


def build_trade_log_table(df):
    """Build recent trade log with styled P&L rendering."""
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None
    closed['datetime'] = pd.to_datetime(closed['date'] + ' ' + closed['time'])
    closed = closed.sort_values('datetime', ascending=False).head(25)
    return closed[['date', 'time', 'symbol', 'action', 'quantity', 'entry', 'exit_price', 'pnl', 'reason']]


def check_market_status():
    """Returns (is_open, status_message)."""
    now = datetime.now()
    
    # 1. Check holiday/weekend
    is_holiday, reason = is_market_holiday(now.date())
    if is_holiday:
        return False, f"Closed ({reason})"
        
    # 2. Check market hours (09:15 to 15:30 IST)
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < market_start:
        return False, "Closed (Pre-Market)"
    elif now > market_end:
        return False, "Closed (Post-Market)"
        
    return True, "Open"


# ══════════════════════════════════════════════════════════════
#  RENDER UI
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">Algodhan Performance Viewer</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Real-Time Quantitative Trading & ETL Analytics Platform — Read-Only Viewer</div>', unsafe_allow_html=True)

# Load data
state = {"status": "OFFLINE", "regime": "WAITING"}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        pass

# Check market status dynamically
is_open, market_status = check_market_status()
if not is_open:
    state['status'] = f"STANDBY ({market_status})"
    state['regime'] = "CLOSED"

df, stats = load_all_data()

# ── ROW 1: Live Status Banner ────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Engine Status", state.get('status', 'OFFLINE'))
m2.metric("Market Regime", state.get('regime', 'NORMAL'))
pnl_delta = "normal" if stats['today_pnl'] >= 0 else "inverse"
m3.metric("Today's P&L", f"₹{stats['today_pnl']:,.2f}", delta=f"₹{stats['today_pnl']:,.2f}", delta_color=pnl_delta)
m4.metric("Portfolio Value", f"₹{stats['total_capital']:,.2f}")

st.markdown("---")

# ── ROW 2: Core Risk Metrics ─────────────────────────────────
st.markdown('<div class="section-header">📈 Portfolio Risk & Performance Metrics</div>', unsafe_allow_html=True)
r1, r2, r3, r4, r5, r6 = st.columns(6)
r1.metric("Sharpe Ratio", f"{stats['sharpe_ratio']:.2f}" if stats['sharpe_ratio'] != 0 else "N/A")
r2.metric("Max Drawdown", f"{stats['max_dd']:.2f}%")
r3.metric("Profit Factor", f"{stats['profit_factor']:.2f}" if stats['profit_factor'] != float('inf') else "∞")
r4.metric("Win Rate", f"{stats['all_time_win_rate']:.1f}%")
r5.metric("Avg Risk:Reward", f"{stats['avg_rr']:.2f}")
r6.metric("Expectancy / Trade", f"₹{stats['expectancy']:.2f}")

st.markdown("---")

# ── Strategy Preview Card ─────────────────────────────────────
st.markdown('<div class="section-header">🛡️ Core Trading Strategy Mechanics</div>', unsafe_allow_html=True)
with st.expander("🔍 Click to view VWAP Pullback Scalper v7 (Institutional Tide) Strategy Details", expanded=True):
    st.markdown("""
    <div style="background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); padding: 18px; border-radius: 12px; margin-bottom: 5px;">
        <h4 style="color:#a5b4fc; margin-top:0;">🌊 VWAP Pullback Scalper v7 — "Institutional Tide"</h4>
        <p style="font-size:0.95rem; color:#94a3b8; line-height:1.6;">
            A multi-timeframe, intraday momentum scalping engine that trades high-liquidity Nifty 50 stocks (like TCS, Reliance, SBIN). 
            Instead of chasing breakouts, the algorithm waits for a confluence of <strong>7 distinct filters</strong> to align before executing.
        </p>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:12px;">
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🎯 Entry Confluence Filters:</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Trend Alignment:</strong> Price must be above 20 EMA and VWAP for BUYS, below for SELLS.</li>
                    <li><strong>Regime Filter:</strong> Underlying Nifty 50 trend & volatility regime must validate direction.</li>
                    <li><strong>Volume Spike:</strong> Entry candle must have volume > 1.5x of the 20-period volume SMA.</li>
                    <li><strong>Momentum:</strong> MACD histogram must be expanding in the trade direction.</li>
                </ul>
            </div>
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🛡️ Risk & Money Management:</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Stop Loss (SL):</strong> Dynamic SL placed at the swing high/low or 1.5x ATR.</li>
                    <li><strong>Target booking:</strong> Take Profit 1 (TP1) at 1:1 Risk-Reward (locks in profit, trails SL to break-even).</li>
                    <li><strong>Trailing SL:</strong> Multi-step trailing SL kicks in past 1.5:1 Risk-Reward.</li>
                    <li><strong>Time Exit:</strong> Intraday positions auto-squared off at 15:15 IST.</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── ROW 3: Equity Curve + Drawdown ───────────────────────────
st.markdown('<div class="section-header">📊 Equity Growth & Underwater Drawdown Curve</div>', unsafe_allow_html=True)
total_cap = float(CAPITAL.get("total", 5000.0))
eq_fig = build_equity_chart(df, total_cap)
if eq_fig:
    st.plotly_chart(eq_fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Equity curve will render once trades are logged.")

st.markdown("---")

# ── ROW 4: Daily P&L + Monthly Heatmap ───────────────────────
col_daily, col_monthly = st.columns([3, 2])

with col_daily:
    st.markdown('<div class="section-header">📉 Daily P&L Distribution</div>', unsafe_allow_html=True)
    daily_fig = build_daily_pnl_chart(df)
    if daily_fig:
        st.plotly_chart(daily_fig, use_container_width=True, config={'displayModeBar': False})

with col_monthly:
    st.markdown('<div class="section-header">🗓️ Monthly Returns Heatmap (%)</div>', unsafe_allow_html=True)
    heatmap_fig = build_monthly_returns_heatmap(df)
    if heatmap_fig:
        st.plotly_chart(heatmap_fig, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")

# ── ROW 5: Symbol Performance + Win/Loss Donut ───────────────
col_sym, col_donut = st.columns([3, 2])

with col_sym:
    st.markdown('<div class="section-header">🏦 P&L by Symbol (Stock-Level Attribution)</div>', unsafe_allow_html=True)
    sym_fig = build_symbol_performance(df)
    if sym_fig:
        st.plotly_chart(sym_fig, use_container_width=True, config={'displayModeBar': False})

with col_donut:
    st.markdown('<div class="section-header">🎯 Trade Outcome Distribution</div>', unsafe_allow_html=True)
    donut_fig = build_win_loss_donut(df)
    if donut_fig:
        st.plotly_chart(donut_fig, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")

# ── ROW 6: Detailed Stats + Today's Trades ───────────────────
col_stats, col_today = st.columns([1, 1])

with col_stats:
    st.markdown('<div class="section-header">🧮 Detailed Trade Statistics</div>', unsafe_allow_html=True)
    stat_data = {
        "Metric": [
            "Total Closed Trades", "All-Time Win Rate", "Avg Winning Trade",
            "Avg Losing Trade", "Best Single Trade", "Worst Single Trade",
            "Max Consecutive Wins", "Max Consecutive Losses",
            "Total Net P&L", "Starting Capital", "Current Portfolio Value"
        ],
        "Value": [
            f"{stats['total_trades']}",
            f"{stats['all_time_win_rate']:.1f}%",
            f"₹{stats['avg_win']:,.2f}",
            f"₹{stats['avg_loss']:,.2f}",
            f"₹{stats['best_trade']:,.2f}",
            f"₹{stats['worst_trade']:,.2f}",
            f"{stats['consecutive_wins']}",
            f"{stats['consecutive_losses']}",
            f"₹{stats['total_pnl']:,.2f}",
            f"₹{total_cap:,.2f}",
            f"₹{stats['total_capital']:,.2f}",
        ]
    }
    st.dataframe(pd.DataFrame(stat_data), hide_index=True, use_container_width=True)

with col_today:
    st.markdown('<div class="section-header">⚡ Today\'s Activity</div>', unsafe_allow_html=True)
    # Open positions
    open_trades = df[df['status'] == 'OPEN'] if (not df.empty and is_open) else pd.DataFrame()
    if not open_trades.empty:
        for _, t in open_trades.iterrows():
            st.markdown(f"""
            <div class="pos-card-open">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-weight:700;color:#e2e8f0;font-size:1.1rem;">{t['symbol']}</span>
                        <span style="font-size:0.75rem;background:rgba(99,102,241,0.2);color:#a5b4fc;padding:2px 8px;border-radius:4px;margin-left:6px;">{t['action']}</span>
                        <div style="color:#94a3b8;font-size:0.8rem;margin-top:3px;">Qty: {t['quantity']} | Entry: ₹{t['entry']:.2f} | SL: ₹{t['stoploss']:.2f}</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.9rem;font-weight:600;color:#a5b4fc;">🔴 LIVE</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        if not is_open:
            st.markdown(f'<div class="no-pos">💤 Market is Closed ({market_status}) — Scanning resumes next trading session at 09:15 IST</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-pos">💎 No active positions — scanning for setups...</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Today's closed trades
    if not df.empty:
        today_str = date.today().isoformat()
        today_closed = df[(df['status'] == 'CLOSED') & (df['date'] == today_str)]
        if not today_closed.empty:
            for _, t in today_closed.sort_values(by='time', ascending=False).iterrows():
                p = float(t['pnl'])
                if p >= 0:
                    st.markdown(f"""
                    <div class="pos-card-win">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-weight:600;color:#e2e8f0;font-size:1.05rem;">{t['symbol']}</span>
                                <span style="font-size:0.7rem;background:rgba(99,102,241,0.15);color:#a5b4fc;padding:2px 6px;border-radius:4px;margin-left:5px;">{t['action']}</span>
                                <div style="color:#94a3b8;font-size:0.78rem;margin-top:2px;">Exit: {t['time']} · {t['reason']}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="font-size:1.15rem;font-weight:800;color:#10b981;">▲ +₹{p:,.2f}</span>
                                <div style="font-size:0.7rem;color:#6ee7b7;">Profit Locked</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="pos-card-loss">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-weight:500;color:#94a3b8;font-size:0.9rem;">{t['symbol']}</span>
                                <span style="font-size:0.65rem;background:rgba(255,255,255,0.04);color:#94a3b8;padding:1px 5px;border-radius:4px;margin-left:5px;">{t['action']}</span>
                                <div style="color:#64748b;font-size:0.7rem;margin-top:2px;">Exit: {t['time']} · {t['reason']}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="font-size:0.95rem;font-weight:500;color:#94a3b8;">▼ -₹{abs(p):,.2f}</span>
                                <div style="font-size:0.65rem;color:#64748b;">Risk Cut</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("---")

# ── ROW 7: Recent Trade Log ──────────────────────────────────
st.markdown('<div class="section-header">📜 Recent Trade Log (Last 25 Executions)</div>', unsafe_allow_html=True)
trade_log = build_trade_log_table(df)
if trade_log is not None:
    st.dataframe(
        trade_log.style.map(
            lambda v: 'color: #10b981; font-weight: 600' if isinstance(v, (int, float)) and v > 0
            else ('color: #ef4444' if isinstance(v, (int, float)) and v < 0 else ''),
            subset=['pnl']
        ),
        hide_index=True,
        use_container_width=True
    )

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Algodhan Quantitative Trading Platform · Built with Python, Pandas, NumPy, SQLite (WAL), WebSockets, Plotly & Streamlit<br>
    Deployed on AWS EC2 · Secured via Nginx Reverse Proxy · Automated Telegram & Email Alerts
</div>
""", unsafe_allow_html=True)

# Auto-refresh
time.sleep(12)
st.rerun()
