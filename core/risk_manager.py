"""
risk_manager.py — Position sizing, daily limits, and trade logging
"""

import sqlite3
from datetime import datetime, date
import os
from config import CAPITAL, STRATEGY


# ══════════════════════════════════════════════════════════════
#  TRADE DATABASE ENGINE
# ══════════════════════════════════════════════════════════════

DB_PATH = "logs/trades.db"

def get_db_conn(path=None):
    if path is None: path = DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT,
            time        TEXT,
            symbol      TEXT,
            action      TEXT,
            quantity    INTEGER,
            entry       REAL,
            stoploss    REAL,
            target      REAL,
            exit_price  REAL,
            pnl         REAL,
            reason      TEXT,
            status      TEXT DEFAULT 'OPEN',
            pt_level    REAL, 
            be_level    REAL, 
            is_partial  INTEGER DEFAULT 0, 
            is_be       INTEGER DEFAULT 0
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS vault (id INTEGER PRIMARY KEY, balance REAL, last_baseline REAL)")
    c.execute("INSERT OR IGNORE INTO vault (id, balance, last_baseline) VALUES (1, 0, ?)", (CAPITAL["total"],))
    conn.commit()
    conn.close()


def log_trade(symbol, action, qty, entry, sl, target, pt, be, reason, db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("""
        INSERT INTO trades (date, time, symbol, action, quantity, entry, stoploss, target, pt_level, be_level, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date.today().isoformat(),
        datetime.now().strftime("%H:%M:%S"),
        symbol, action, qty,
        entry, sl, target, pt, be, reason
    ))
    trade_id = c.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def get_open_trades(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT id, symbol, action, quantity, entry, stoploss, target, pt_level, be_level, is_partial, is_be FROM trades WHERE status='OPEN'")
    rows = c.fetchall()
    conn.close()
    return rows

def update_trade_state(trade_id, is_partial=None, is_be=None, sl=None, db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    if is_partial is not None: c.execute("UPDATE trades SET is_partial=? WHERE id=?", (is_partial, trade_id))
    if is_be is not None: c.execute("UPDATE trades SET is_be=? WHERE id=?", (is_be, trade_id))
    if sl is not None: c.execute("UPDATE trades SET stoploss=? WHERE id=?", (sl, trade_id))
    conn.commit()
    conn.close()


def close_trade(trade_id, exit_price, db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT action, quantity, entry FROM trades WHERE id=?", (trade_id,))
    row = c.fetchone()
    if row:
        action, qty, entry = row
        pnl = (exit_price - entry) * qty if action == "BUY" else (entry - exit_price) * qty
        # Sanity check for glitched data
        if exit_price > entry * 5 or exit_price < entry / 5:
             pnl = 0.0
             
        c.execute("""
            UPDATE trades SET exit_price=?, pnl=?, status='CLOSED' WHERE id=?
        """, (exit_price, round(pnl, 2), trade_id))
    conn.commit()
    conn.close()

def get_today_trade_count(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE date=?", (date.today().isoformat(),))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_open_trade_count(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE status='OPEN'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_pnl(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT SUM(pnl) FROM trades WHERE date=? AND status='CLOSED'", (date.today().isoformat(),))
    result = c.fetchone()[0]
    conn.close()
    return result or 0.0

def get_total_pnl_all_time(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT SUM(pnl) FROM trades WHERE status='CLOSED'")
    result = c.fetchone()[0]
    conn.close()
    return result or 0.0

def get_total_capital(db_path=None):
    if not STRATEGY.get("compounding_enabled"):
        return CAPITAL["total"]
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT balance FROM vault WHERE id=1")
    vault_balance = c.fetchone()[0]
    conn.close()
    pnl = get_total_pnl_all_time(db_path)
    return (CAPITAL["total"] + pnl) - vault_balance

def calculate_quantity(entry_price, stoploss_price):
    risk_pct = STRATEGY["risk_per_trade_pct"] / 100
    total_cap = get_total_capital()
    risk_amount = total_cap * risk_pct
    risk_per_share = abs(entry_price - stoploss_price)
    if risk_per_share == 0: return 1
    return max(int(risk_amount / risk_per_share), 1)

def can_trade(already_traded_symbols=None):
    trade_count = get_today_trade_count()
    if trade_count >= STRATEGY["max_trades_per_day"]:
        return False, "Max trades reached"
    today_pnl = get_today_pnl()
    if today_pnl < -(CAPITAL["total"] * 0.02):
        return False, "Daily loss limit hit"
    return True, "OK"

def get_today_summary(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT symbol, action, quantity, entry, exit_price, pnl, status
        FROM trades WHERE date=?
    """, (date.today().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows

def get_vault_status(db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("SELECT balance, last_baseline FROM vault WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row

def bank_profit_live(amount, new_baseline, db_path=None):
    conn = get_db_conn(db_path)
    c = conn.cursor()
    c.execute("UPDATE vault SET balance = balance + ?, last_baseline = ? WHERE id=1", (amount, new_baseline))
    conn.commit()
    conn.close()
