"""
notifier.py — Professional Notification Manager
Handles Telegram alerts and Email reports with attachment support.
"""

import requests
import logging
import smtplib
from datetime import date
from typing import List, Tuple, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from config import TELEGRAM, EMAIL_REPORTING

log = logging.getLogger(__name__)

def send(message: str) -> None:
    """Sends a formatted message to the configured Telegram chat."""
    if not TELEGRAM["enabled"]:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM['bot_token']}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM["chat_id"],
            "text": message,
            "parse_mode": "HTML"
        }, timeout=5)
        if not resp.ok:
            log.error(f"Telegram API Error: {resp.text}")
    except Exception as e:
        log.error(f"Telegram Connection Error: {e}")

def signal_alert(symbol: str, direction: int, entry: float, sl: float, 
                 target: float, reason: str, strength: int) -> None:
    """Sends a detailed trade signal alert to Telegram."""
    emoji = "🟢 LONG" if direction == 1 else "🔴 SHORT"
    msg = (
        f"<b>{emoji} SIGNAL — {symbol}</b>\n"
        f"Entry   : ₹{entry}\n"
        f"Stop Loss: ₹{sl}\n"
        f"Target  : ₹{target}\n"
        f"Strength: {strength}/4 strategies\n"
        f"Reason  : {reason}"
    )
    send(msg)

def order_alert(symbol: str, action: str, qty: int, order_id: Optional[str]) -> None:
    """Sends an order execution status alert to Telegram."""
    emoji = "✅" if order_id else "❌"
    msg = (
        f"{emoji} <b>ORDER — {symbol}</b>\n"
        f"Action: {action}  Qty: {qty}\n"
        f"Order ID: {order_id or 'FAILED'}"
    )
    send(msg)

def daily_summary(trades: List[Tuple[Any, ...]], total_pnl: float) -> None:
    """Sends the end-of-day summary to both Telegram and Email."""
    msg = f"<b>📊 DAY SUMMARY: {date.today()}</b>\n"
    msg += f"Total P&L: ₹{total_pnl:.2f}\n\n"
    
    table = ""
    for t in trades:
        # t: (symbol, action, quantity, entry, exit, pnl, status)
        pnl = t[5] if t[5] is not None else 0.0
        icon = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
        table += f"{icon} {t[0]} | {t[1]} | P&L: ₹{pnl:.2f}\n"
    
    send(msg + table)
    send_email_report(msg + table)

def send_email_report(body: str) -> None:
    """Sends a text-based trade report via Gmail SMTP."""
    if not EMAIL_REPORTING["enabled"]:
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REPORTING["sender_email"]
        msg['To'] = EMAIL_REPORTING["receiver_email"]
        msg['Subject'] = f"Algodhan Daily Trade Report - {date.today()}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        _transmit_email(msg)
        log.info("Email report sent successfully")
    except Exception as e:
        log.error(f"Failed to send email report: {e}")

def send_file_to_email(file_path: str, subject: Optional[str] = None) -> None:
    """Sends a specific file as an email attachment."""
    if not EMAIL_REPORTING["enabled"]:
        return
        
    try:
        import os
        filename = os.path.basename(file_path)
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REPORTING["sender_email"]
        msg['To'] = EMAIL_REPORTING["receiver_email"]
        msg['Subject'] = subject or f"Algodhan File Export: {filename}"
        
        msg.attach(MIMEText(f"Please find the attached file: {filename}", 'plain'))
        
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)
            
        _transmit_email(msg)
        log.info(f"Email with attachment {filename} sent successfully")
    except Exception as e:
        log.error(f"Failed to send email attachment: {e}")

def bot_status(status: str, detail: str = "") -> None:
    """Sends a general bot status update (Wake up, Shutdown, etc.)"""
    emoji = "🤖"
    if "wake" in status.lower() or "start" in status.lower(): emoji = "☀️"
    elif "stop" in status.lower() or "shutdown" in status.lower(): emoji = "🌙"
    elif "error" in status.lower(): emoji = "⚠️"
    
    msg = f"<b>{emoji} {status.upper()}</b>\n{detail}"
    send(msg)

def auth_status(success: bool, detail: str = "") -> None:
    """Sends an authentication success or failure alert."""
    emoji = "🔑" if success else "🚫"
    title = "AUTH SUCCESS" if success else "AUTH FAILED"
    msg = f"<b>{emoji} {title}</b>\n{detail}"
    send(msg)

def scanning_update(winners: List[str], losers: List[str]) -> None:
    """Sends a summary of the Nifty 100 heat-map scan."""
    msg = (
        "<b>🔍 MARKET SCAN COMPLETE</b>\n\n"
        f"🔥 <b>Winners:</b> {', '.join(winners[:5])}\n"
        f"❄️ <b>Losers:</b> {', '.join(losers[:5])}\n\n"
        "<i>Watchlist updated with top movers.</i>"
    )
    send(msg)

def _transmit_email(msg: MIMEMultipart) -> None:
    """Internal helper to handle SMTP transmission."""
    try:
        server = smtplib.SMTP(EMAIL_REPORTING["smtp_server"], EMAIL_REPORTING["smtp_port"])
        server.starttls()
        server.login(EMAIL_REPORTING["sender_email"], EMAIL_REPORTING["app_password"])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        log.error(f"Email transmission error: {e}")
