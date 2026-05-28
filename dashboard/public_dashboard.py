"""
public_dashboard.py — Smart-Trade Performance Viewer
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
    page_title="Smart-Trade — Quantitative Performance Analytics",
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
DB_PATH_MAIN = "logs/trades.db"
STATE_FILE_MAIN = "logs/system_state.json"

DB_PATH_V8 = "logs/v8_trades.db"
STATE_FILE_V8 = "logs/v8/system_state.json"

@st.cache_data(ttl=8)
def load_all_data(db_path, total_cap):
    """Load and compute all analytics from the trade database."""
    default_stats = {
        "today_pnl": 0.0, "total_pnl": 0.0, "today_count": 0, "win_rate": 0.0,
        "total_trades": 0, "all_time_win_rate": 0.0, "sharpe_ratio": 0.0,
        "max_dd": 0.0, "profit_factor": 1.0, "avg_win": 0.0, "avg_loss": 0.0,
        "best_trade": 0.0, "worst_trade": 0.0, "expectancy": 0.0,
        "avg_rr": 0.0, "consecutive_wins": 0, "consecutive_losses": 0,
        "total_capital": total_cap
    }
    if not os.path.exists(db_path):
        return pd.DataFrame(), default_stats

    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA busy_timeout = 3000;")
        df = pd.read_sql("SELECT * FROM trades", conn)
    except Exception as e:
        import sys
        print(f"Error loading trade data from {db_path}: {e}", file=sys.stderr)
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
    if pnl_series:
        equity = [total_cap]
        for p in pnl_series:
            equity.append(equity[-1] + p)
        equity_s = pd.Series(equity)
        cum_max = equity_s.cummax()
        drawdowns = (equity_s - cum_max) / cum_max * 100
        max_dd = float(drawdowns.min())
    else:
        max_dd = 0.0

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


# ── Live paper-trade start date (all data before this is simulated) ──────────
LIVE_START_DATE = "2026-04-09"   # Go-live paper trading start date
LIVE_START_CAPITAL = 100_000.0   # Fresh starting capital for live chart

def build_equity_chart(df, total_cap):
    """
    Build Plotly equity curve showing ONLY real live paper-trade results.
    All backtest / simulated data (before LIVE_START_DATE) is excluded.
    Chart starts at LIVE_START_CAPITAL (₹10,000) on the go-live date.
    """
    closed = df[df['status'] == 'CLOSED'].copy()
    if closed.empty:
        return None

    closed['datetime'] = pd.to_datetime(closed['date'] + ' ' + closed['time'])
    closed = closed.sort_values('datetime')

    # ── Filter to ONLY live paper-trade data ──────────────────────────────
    live_cutoff = pd.Timestamp(LIVE_START_DATE)
    live = closed[closed['datetime'] >= live_cutoff].copy()

    if live.empty:
        return None

    # ── Build cumulative equity starting at LIVE_START_CAPITAL ───────────
    equity_vals = [LIVE_START_CAPITAL]
    for p in live['pnl'].astype(float):
        equity_vals.append(equity_vals[-1] + p)

    # X-axis: seed point 5 min before first trade, then each trade timestamp
    timestamps = (
        [live['datetime'].iloc[0] - pd.Timedelta(minutes=5)]
        + live['datetime'].tolist()
    )

    # ── Drawdown — computed purely on live equity ─────────────────────────
    eq_s   = pd.Series(equity_vals)
    peak   = eq_s.cummax()
    dd_pct = ((eq_s - peak) / peak * 100).clip(lower=-40)

    # ── Running colour: green above start, red below ──────────────────────
    pnl_delta = equity_vals[-1] - LIVE_START_CAPITAL
    equity_color      = '#10b981' if pnl_delta >= 0 else '#ef4444'
    equity_fill_color = 'rgba(16,185,129,0.07)' if pnl_delta >= 0 else 'rgba(239,68,68,0.07)'

    fig = go.Figure()

    # ── Drawdown fill (subtle red underlay) ───────────────────────────────
    fig.add_trace(go.Scatter(
        x=timestamps, y=dd_pct,
        name="Drawdown %",
        fill='tozeroy', fillcolor='rgba(239,68,68,0.07)',
        line=dict(color='rgba(239,68,68,0.3)', width=1),
        yaxis='y2',
        hovertemplate='Drawdown: %{y:.2f}%<extra></extra>'
    ))

    # ── Equity line (live paper trade only) ───────────────────────────────
    fig.add_trace(go.Scatter(
        x=timestamps, y=equity_vals,
        name="🟢 Live Paper Trade (from 25 May)",
        line=dict(color=equity_color, width=2.8, shape='spline'),
        fill='tozeroy', fillcolor=equity_fill_color,
        hovertemplate='₹%{y:,.2f}<extra></extra>'
    ))

    # ── Starting capital reference line ───────────────────────────────────
    fig.add_hline(
        y=LIVE_START_CAPITAL,
        line=dict(color='rgba(148,163,184,0.3)', width=1, dash='dot'),
    )
    fig.add_annotation(
        x=timestamps[0], y=LIVE_START_CAPITAL,
        text=f" Start ₹{LIVE_START_CAPITAL:,.0f}",
        showarrow=False,
        font=dict(color='#64748b', size=10, family='Outfit, sans-serif'),
        xanchor='left', yanchor='bottom',
    )

    # ── Current value callout on the last point ───────────────────────────
    current_val = equity_vals[-1]
    gain_pct    = (current_val - LIVE_START_CAPITAL) / LIVE_START_CAPITAL * 100
    gain_sign   = "+" if gain_pct >= 0 else ""
    fig.add_annotation(
        x=timestamps[-1], y=current_val,
        text=f" ₹{current_val:,.0f} ({gain_sign}{gain_pct:.1f}%)",
        showarrow=False,
        font=dict(color=equity_color, size=11, family='Outfit, sans-serif'),
        xanchor='left', yanchor='middle',
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#94a3b8", size=13),
        margin=dict(l=40, r=80, t=50, b=40),
        hoverlabel=dict(
            bgcolor="#1e1e2e", font_color="#e2e8f0",
            bordercolor="rgba(99,102,241,0.3)"
        ),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11)),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.06)",
            title="Date"
        ),
        yaxis=dict(
            title="Equity (₹)", gridcolor="rgba(255,255,255,0.04)", side='left'
        ),
        yaxis2=dict(
            title="Drawdown %", overlaying='y', side='right',
            gridcolor="rgba(255,255,255,0.02)",
            range=[max(float(dd_pct.min()) * 1.5, -45), 5]
        ),
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
    total_cap = 100_000.0
    monthly['return_pct'] = (monthly['pnl'] / total_cap) * 100

    pivot = monthly.pivot(index='year', columns='month', values='return_pct').fillna(0)
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
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
    
    is_holiday, reason = is_market_holiday(now.date())
    if is_holiday:
        return False, f"Closed ({reason})"
        
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < market_start:
        return False, "Closed (Pre-Market)"
    elif now > market_end:
        return False, "Closed (Post-Market)"
        
    return True, "Open"


def get_bot_health(state_file_path):
    """Checks if the bot is running based on its state file modification time."""
    if not os.path.exists(state_file_path):
        return False, {"status": "OFFLINE", "regime": "OFFLINE"}
    try:
        mtime = os.path.getmtime(state_file_path)
        is_running = (time.time() - mtime) < 120
        with open(state_file_path, "r") as f:
            state = json.load(f)
        return is_running, state
    except Exception:
        return False, {"status": "OFFLINE", "regime": "OFFLINE"}


@st.cache_data(ttl=3600)
def load_backtest_data(trades_csv, equity_csv):
    if not os.path.exists(trades_csv) or not os.path.exists(equity_csv):
        return pd.DataFrame(), pd.DataFrame(), {}
    try:
        trades = pd.read_csv(trades_csv)
        equity = pd.read_csv(equity_csv)
        total_trades = len(trades)
        if total_trades == 0:
            return trades, equity, {}
        wins = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] < 0]
        win_rate = (len(wins) / total_trades) * 100
        total_pnl = float(trades['pnl'].sum())
        start_cap = 10000.0
        final_cap = float(equity['cap'].iloc[-1])
        net_return = ((final_cap - start_cap) / start_cap) * 100
        
        equity['peak'] = equity['cap'].cummax()
        equity['drawdown'] = (equity['cap'] - equity['peak']) / equity['peak'] * 100
        max_dd = float(equity['drawdown'].min())
        
        gross_profits = float(wins['pnl'].sum())
        gross_losses = float(abs(losses['pnl'].sum()))
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else 1.0
        
        daily_returns = equity['cap'].pct_change().dropna()
        sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 1 and daily_returns.std() > 0 else 0.0
        
        stats = {
            "net_pnl": total_pnl,
            "net_return": net_return,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "max_dd": max_dd,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "final_cap": final_cap
        }
        return trades, equity, stats
    except Exception as e:
        import sys
        print(f"Error loading backtest files: {e}", file=sys.stderr)
        return pd.DataFrame(), pd.DataFrame(), {}


def build_backtest_chart(equity_df, bot_name, line_color, fill_color):
    if equity_df.empty:
        return None
    try:
        eq = equity_df.copy()
        eq['date'] = pd.to_datetime(eq['date'])
        
        fig = go.Figure()
        
        eq['peak'] = eq['cap'].cummax()
        eq['drawdown'] = (eq['cap'] - eq['peak']) / eq['peak'] * 100
        
        fig.add_trace(go.Scatter(
            x=eq['date'], y=eq['drawdown'],
            name="Drawdown %",
            fill='tozeroy', fillcolor='rgba(239,68,68,0.05)',
            line=dict(color='rgba(239,68,68,0.2)', width=1),
            yaxis='y2',
            hovertemplate='Drawdown: %{y:.2f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=eq['date'], y=eq['cap'],
            name=f"Compounding Equity ({bot_name})",
            line=dict(color=line_color, width=2.5, shape='spline'),
            fill='tozeroy', fillcolor=fill_color,
            hovertemplate='₹%{y:,.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#94a3b8", size=13),
            margin=dict(l=50, r=50, t=10, b=30),
            hoverlabel=dict(bgcolor="#1e1e2e", font_color="#e2e8f0", bordercolor="rgba(99,102,241,0.3)"),
            height=300,
            showlegend=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.03)", zerolinecolor="rgba(255,255,255,0.05)", title=""),
            yaxis=dict(title="Equity (₹)", gridcolor="rgba(255,255,255,0.03)", side='left'),
            yaxis2=dict(title="Drawdown %", overlaying='y', side='right', gridcolor="rgba(255,255,255,0.01)", range=[-30, 2]),
        )
        return fig
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  RENDER BOT DAILY STATS HELPER
# ══════════════════════════════════════════════════════════════
def render_daily_activity_section(df, is_open, market_status):
    """Renders active positions and today's closed trades in a premium styling."""
    # Active Positions
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
            st.markdown(f'<div class="no-pos">💤 Market is Closed ({market_status})</div>', unsafe_allow_html=True)
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
        else:
            st.write("No trades closed yet today.")


# ══════════════════════════════════════════════════════════════
#  RENDER BOT DEEP ANALYTICS HELPER
# ══════════════════════════════════════════════════════════════
def render_bot_analytics(df, stats, total_cap, bot_name, strategy_name, strategy_desc_html):
    """Renders deep analytics, equity curves, heatmaps and logs for a single bot."""
    # ── ROW 2: Core Risk Metrics ─────────────────────────────────
    st.markdown(f'<div class="section-header">📈 {bot_name} Risk & Performance Metrics</div>', unsafe_allow_html=True)
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
    with st.expander(f"🔍 Click to view {strategy_name} Strategy Details", expanded=True):
        st.markdown(strategy_desc_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── ROW 3: Equity Curve + Drawdown ───────────────────────────
    st.markdown('<div class="section-header">📊 Equity Growth & Underwater Drawdown Curve</div>', unsafe_allow_html=True)
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

    # ── ROW 6: Detailed Stats + Recent Trade Log ───────────────────
    col_stats, col_log = st.columns([2, 3])

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

    with col_log:
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
        else:
            st.info("No trade log entries to display.")


# ══════════════════════════════════════════════════════════════
#  RENDER MAIN UI
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">Smart-Trade Performance Viewer</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Real-Time Quantitative Trading & ETL Analytics Platform — Read-Only Viewer</div>', unsafe_allow_html=True)

# 1. Load bot healths
bot_is_running_main, state_main = get_bot_health(STATE_FILE_MAIN)
bot_is_running_v8, state_v8 = get_bot_health(STATE_FILE_V8)

# 2. Check market status
is_open, market_status = check_market_status()

# 3. Clean up status based on market hours
for state, health in [(state_main, bot_is_running_main), (state_v8, bot_is_running_v8)]:
    if health:
        if not is_open:
            if state.get('status') == "RUNNING":
                state['status'] = f"RUNNING ({market_status})"
            if state.get('regime') in [None, "WAITING"]:
                state['regime'] = "STANDBY"
    else:
        if not is_open:
            state['status'] = f"OFFLINE ({market_status})"
            state['regime'] = "CLOSED"
        else:
            state['status'] = "OFFLINE"
            state['regime'] = "OFFLINE"

# 4. Load Data
total_cap = 100_000.0
df_main, stats_main = load_all_data(DB_PATH_MAIN, total_cap)
df_v8, stats_v8 = load_all_data(DB_PATH_V8, total_cap)

# 5. Compute LIVE-ONLY portfolio values (trades from LIVE_START_DATE only)
#    This prevents backtest / simulated P&L inflating the live board metric.
def _live_portfolio(df, start_date=LIVE_START_DATE, start_capital=LIVE_START_CAPITAL):
    """Returns LIVE_START_CAPITAL + sum of P&L from trades on/after start_date."""
    if df.empty:
        return start_capital
    closed = df[df['status'] == 'CLOSED'].copy()
    live_closed = closed[closed['date'] >= start_date]
    return start_capital + float(live_closed['pnl'].sum())

live_portfolio_main = _live_portfolio(df_main)
live_portfolio_v8   = _live_portfolio(df_v8)

# Create Page Tabs
tab_daily, tab_main, tab_v8 = st.tabs([
    "📊 Live Daily Performance (Both Bots)", 
    "🌊 Main Bot (v15 Live) Analytics", 
    "⚡ Experimental Bot (v8 Paper) Analytics"
])

# ── TAB 1: Live Daily Performance (Both Bots) ──────────────────
with tab_daily:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 style="color:#6366f1; border-bottom: 2px solid rgba(99,102,241,0.2); padding-bottom: 6px;">🌊 Main Bot (v15 Live)</h3>', unsafe_allow_html=True)
        
        # Live Stats Column 1
        m1, m2 = st.columns(2)
        m1.metric("Engine Status", state_main.get('status', 'OFFLINE'))
        m2.metric("Market Regime", state_main.get('regime', 'NORMAL'))
        
        m3, m4 = st.columns(2)
        pnl_delta_main = "normal" if stats_main['today_pnl'] >= 0 else "inverse"
        m3.metric("Today's P&L", f"₹{stats_main['today_pnl']:,.2f}", delta=f"₹{stats_main['today_pnl']:,.2f}", delta_color=pnl_delta_main)
        live_gain_main = live_portfolio_main - LIVE_START_CAPITAL
        m4.metric("Live Portfolio", f"₹{live_portfolio_main:,.2f}",
                  delta=f"₹{live_gain_main:+,.2f} since {LIVE_START_DATE}",
                  delta_color="normal" if live_gain_main >= 0 else "inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">⚡ Today\'s Activity & Trade Log</div>', unsafe_allow_html=True)
        render_daily_activity_section(df_main, is_open, market_status)
        
    with col2:
        st.markdown('<h3 style="color:#a855f7; border-bottom: 2px solid rgba(168,85,247,0.2); padding-bottom: 6px;">⚡ Experimental Bot (v8 Paper)</h3>', unsafe_allow_html=True)
        
        # Live Stats Column 2
        v1, v2 = st.columns(2)
        v1.metric("Engine Status", state_v8.get('status', 'OFFLINE'))
        v2.metric("Market Regime", state_v8.get('regime', 'NORMAL'))
        
        v3, v4 = st.columns(2)
        pnl_delta_v8 = "normal" if stats_v8['today_pnl'] >= 0 else "inverse"
        v3.metric("Today's P&L", f"₹{stats_v8['today_pnl']:,.2f}", delta=f"₹{stats_v8['today_pnl']:,.2f}", delta_color=pnl_delta_v8)
        live_gain_v8 = live_portfolio_v8 - LIVE_START_CAPITAL
        v4.metric("Live Portfolio", f"₹{live_portfolio_v8:,.2f}",
                  delta=f"₹{live_gain_v8:+,.2f} since {LIVE_START_DATE}",
                  delta_color="normal" if live_gain_v8 >= 0 else "inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">⚡ Today\'s Activity & Trade Log</div>', unsafe_allow_html=True)
        render_daily_activity_section(df_v8, is_open, market_status)

    # ── 2-Year Compounding Backtest Section ──────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<h2 style="text-align: center; color: #a855f7; margin-bottom: 24px; border-bottom: 2px solid rgba(168,85,247,0.2); padding-bottom: 8px;">📊 2-Year Compounding Backtest Performance (2023 - 2024)</h2>', unsafe_allow_html=True)
    
    # Load backtest data
    bt_trades_main, bt_equity_main, bt_stats_main = load_backtest_data("logs/backtest_2023_24_v15_trades.csv", "logs/backtest_2023_24_v15_equity.csv")
    bt_trades_v8, bt_equity_v8, bt_stats_v8 = load_backtest_data("logs/backtest_2023_24_v8_trades.csv", "logs/backtest_2023_24_v8_equity.csv")
    
    col_bt1, col_bt2 = st.columns(2)
    
    with col_bt1:
        st.markdown('<h4 style="color:#6366f1; margin-bottom: 12px; text-align: center;">🌊 Main Bot (v15 Live) Historical Performance</h4>', unsafe_allow_html=True)
        if not bt_stats_main:
            st.info("No backtest data found.")
        else:
            # Metrics Row 1
            m_r1, m_r2, m_r3 = st.columns(3)
            m_r1.metric("Historical P&L", f"₹{bt_stats_main['net_pnl']:,.2f}", f"+{bt_stats_main['net_return']:.1f}%")
            m_r2.metric("Win Rate", f"{bt_stats_main['win_rate']:.1f}%")
            m_r3.metric("Max Drawdown", f"{bt_stats_main['max_dd']:.1f}%")
            
            # Metrics Row 2
            m_r4, m_r5, m_r6 = st.columns(3)
            m_r4.metric("Sharpe Ratio", f"{bt_stats_main['sharpe']:.2f}")
            m_r5.metric("Profit Factor", f"{bt_stats_main['profit_factor']:.2f}")
            m_r6.metric("Total Trades", f"{bt_stats_main['total_trades']}")
            
            # Chart
            fig_main = build_backtest_chart(bt_equity_main, "Main Bot (v15)", "#6366f1", "rgba(99,102,241,0.08)")
            if fig_main:
                st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': False})
                
    with col_bt2:
        st.markdown('<h4 style="color:#a855f7; margin-bottom: 12px; text-align: center;">⚡ Experimental Bot (v8 Paper) Historical Performance</h4>', unsafe_allow_html=True)
        if not bt_stats_v8:
            st.info("No backtest data found.")
        else:
            # Metrics Row 1
            v_r1, v_r2, v_r3 = st.columns(3)
            v_r1.metric("Historical P&L", f"₹{bt_stats_v8['net_pnl']:,.2f}", f"+{bt_stats_v8['net_return']:.1f}%")
            v_r2.metric("Win Rate", f"{bt_stats_v8['win_rate']:.1f}%")
            v_r3.metric("Max Drawdown", f"{bt_stats_v8['max_dd']:.1f}%")
            
            # Metrics Row 2
            v_r4, v_r5, v_r6 = st.columns(3)
            v_r4.metric("Sharpe Ratio", f"{bt_stats_v8['sharpe']:.2f}")
            v_r5.metric("Profit Factor", f"{bt_stats_v8['profit_factor']:.2f}")
            v_r6.metric("Total Trades", f"{bt_stats_v8['total_trades']}")
            
            # Chart
            fig_v8 = build_backtest_chart(bt_equity_v8, "Experimental Bot (v8)", "#a855f7", "rgba(168,85,247,0.08)")
            if fig_v8:
                st.plotly_chart(fig_v8, use_container_width=True, config={'displayModeBar': False})

# ── TAB 2: Main Bot Deep Analytics ─────────────────────────────
with tab_main:
    strategy_desc_main = """
    <div style="background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); padding: 18px; border-radius: 12px; margin-bottom: 5px;">
        <h4 style="color:#a5b4fc; margin-top:0;">🌊 VWAP Pullback Scalper v13 — "Institutional Tide" (God Mode v15)</h4>
        <p style="font-size:0.95rem; color:#94a3b8; line-height:1.6;">
            A multi-timeframe, intraday momentum scalping engine that trades high-liquidity Nifty 50 stocks (like TCS, Reliance, SBIN). 
            Instead of chasing breakouts, the algorithm waits for a confluence of <strong>7 distinct filters</strong> to align before executing.
        </p>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:12px;">
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🎯 Entry Confluence Filters (all 7 must pass):</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Trend Alignment:</strong> Price must be above EMA21 and VWAP for BUYS, below for SELLS.</li>
                    <li><strong>15-Min EMA Alignment:</strong> Price above EMA21 on the 15-minute chart for BUYS, below for SELLS.</li>
                    <li><strong>EMA9 Direction:</strong> EMA9 must be rising (BUYS) or falling (SELLS) on the signal candle.</li>
                    <li><strong>RSI Pullback Zone:</strong> RSI must dip below 50 before recovering above 40 (BUYS), or above 50 before falling below 60 (SELLS).</li>
                    <li><strong>Regime Filter:</strong> Underlying Nifty 50 trend & volatility regime must validate direction.</li>
                    <li><strong>Volume Spike:</strong> Entry candle must have volume > 1.8x of the 20-period volume SMA.</li>
                    <li><strong>MACD Acceleration:</strong> MACD histogram must be expanding in the trade direction.</li>
                </ul>
            </div>
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🛡️ Risk & Money Management:</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Stop Loss (SL):</strong> Dynamic SL placed at 1.2x ATR from entry.</li>
                    <li><strong>Partial TP (TP1):</strong> 25% position exited at 1:1 Risk-Reward — SL moved to Break-Even.</li>
                    <li><strong>Final Target:</strong> Remaining position targets a 2.5:1 Risk-Reward ratio.</li>
                    <li><strong>Break-Even Trigger:</strong> SL shifts to entry + 0.2% fee buffer once TP1 is hit.</li>
                    <li><strong>Trailing SL:</strong> <em>Planned feature — currently disabled in live config.</em></li>
                    <li><strong>Time Exit:</strong> Intraday positions auto-squared off at 15:25 IST.</li>
                </ul>
            </div>
        </div>
    </div>
    """
    render_bot_analytics(df_main, stats_main, total_cap, "Main Bot (v15 Live)", "VWAP Pullback Scalper v13 (God Mode v15)", strategy_desc_main)

# ── TAB 3: Experimental Bot Deep Analytics ──────────────────────
with tab_v8:
    strategy_desc_v8 = """
    <div style="background: rgba(168, 85, 247, 0.03); border: 1px solid rgba(168, 85, 247, 0.1); padding: 18px; border-radius: 12px; margin-bottom: 5px;">
        <h4 style="color:#c084fc; margin-top:0;">⚡ VWAP Pullback Scalper v8 — "Regime Switch Edition"</h4>
        <p style="font-size:0.95rem; color:#94a3b8; line-height:1.6;">
            An advanced adaptive algorithmic trading engine designed to identify the prevailing market structure and dynamically switch core strategies.
            Rather than relying on a static set of indicators, it scans ADX and Choppiness index to categorize the market state.
        </p>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:12px;">
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🔄 Adaptive Market Regimes:</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Trending Regime (TREND_UP / TREND_DOWN):</strong> Executes high-conviction pullback entries near VWAP / EMA21 on volume validation.</li>
                    <li><strong>Range-Bound Regime (SIDEWAYS):</strong> Targets mean-reversion rejections near Previous Day High (PDH) and Previous Day Low (PDL).</li>
                    <li><strong>Choppy Regime (CHOPPY):</strong> Enforces strict sit-out logic to conserve capital and avoid market noise.</li>
                </ul>
            </div>
            <div>
                <strong style="color:#e2e8f0; font-size:0.9rem;">🛡️ Risk & Strategy Controls:</strong>
                <ul style="font-size:0.85rem; color:#94a3b8; margin: 4px 0 0 16px; padding:0;">
                    <li><strong>Stop Loss (SL):</strong> Placed below PDL (for range buys), above PDH (for range sells), or 1.5x ATR (for trend pullbacks).</li>
                    <li><strong>Targets:</strong> Locks profits at the range midpoint (for ranges) or targets a 2.0x Risk-Reward (for trends).</li>
                    <li><strong>Self-Healing Engine:</strong> Implements our new robust <strong>Dynamic Break-Even Trigger</strong> to prevent fee-buffer trade cuts.</li>
                </ul>
            </div>
        </div>
    </div>
    """
    render_bot_analytics(df_v8, stats_v8, total_cap, "Experimental Bot (v8 Paper)", "VWAP Pullback Scalper v8", strategy_desc_v8)


# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Smart-Trade Quantitative Trading Platform · Built with Python, Pandas, NumPy, SQLite (WAL), WebSockets, Plotly & Streamlit<br>
    Deployed on AWS EC2 · Secured via Nginx Reverse Proxy · Automated Telegram & Email Alerts
</div>
""", unsafe_allow_html=True)

# Auto-refresh
time.sleep(12)
st.rerun()
