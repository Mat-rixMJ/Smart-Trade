import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID", "DEMO_CLIENT_ID")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "DEMO_ACCESS_TOKEN")

# Risk Settings
RISK_PER_TRADE_PCT = 1.5
MAX_DRAWDOWN_PCT = 3.0
CAPITAL = 100000

# Trading Parameters
SYMBOLS = ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]
TIMEFRAME = "5"
