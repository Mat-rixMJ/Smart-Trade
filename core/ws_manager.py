"""
ws_manager.py - Professional DhanHQ WebSocket Manager
Manages real-time tick data with heartbeat monitoring and auto-reconnection.
"""

import os
import time
import threading
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)

# Global state for monitoring
LTP_DICT: Dict[str, float] = {}
LAST_TICK_TIME: float = time.time()  # Initialize to current time
WS_FEED: Any = None
WS_PARAMS: Dict[str, Any] = {}

def on_message(ws: Any, message: Any) -> None:
    """Callback for every tick received from WebSocket."""
    global LAST_TICK_TIME
    if not isinstance(message, dict):
        return
        
    if message.get("type") == "Ticker Data":
        sec_id = message.get("security_id")
        ltp = message.get("LTP")
        if sec_id and ltp:
            # Update global LTP state
            LTP_DICT[str(sec_id)] = float(ltp)
            LAST_TICK_TIME = time.time()

def on_error(ws: Any, error: Any) -> None:
    """Handles WebSocket errors."""
    log.error(f"WebSocket Error: {error}")

def on_close(ws: Any, close_status_code: int, close_msg: str) -> None:
    """Handles WebSocket closure events."""
    log.warning(f"WebSocket Closed: {close_status_code} - {close_msg}")

def on_connect(ws: Any) -> None:
    """Callback triggered on successful connection."""
    log.info("[OK] WebSocket Connected Successfully!")

MONITOR_STARTED: bool = False

def stop_websocket() -> None:
    """Closes and releases the active WebSocket connection gracefully."""
    global WS_FEED
    if WS_FEED is not None:
        try:
            log.info("🔌 Closing active WebSocket connection...")
            if hasattr(WS_FEED, "close_connection"):
                WS_FEED.close_connection()
            elif hasattr(WS_FEED, "disconnect"):
                WS_FEED.disconnect()
            elif hasattr(WS_FEED, "close"):
                WS_FEED.close()
            log.info("✅ WebSocket closed successfully.")
        except Exception as e:
            log.error(f"Error closing WebSocket: {e}")
        WS_FEED = None

def start_websocket(client_id: str, access_token: str, symbols: List[str], broker_type: str = "dhan") -> Any:
    """
    Initializes the WebSocket (Dhan or Fyers) and starts the heartbeat monitor.
    """
    global WS_PARAMS, MONITOR_STARTED
    WS_PARAMS = {
        'client_id': client_id, 
        'access_token': access_token, 
        'symbols': symbols,
        'broker_type': broker_type
    }
    
    stop_websocket()  # Gracefully close any existing connection first!
    
    if broker_type == "fyers":
        feed = _init_fyers_ws(client_id, access_token, symbols)
    else:
        feed = _init_ws(client_id, access_token, symbols)
    
    # Start the Heartbeat Monitor Thread ONLY ONCE
    if not MONITOR_STARTED:
        monitor_thread = threading.Thread(target=_connection_monitor, daemon=True)
        monitor_thread.name = "WS-Monitor-Thread"
        monitor_thread.start()
        MONITOR_STARTED = True
    
    return feed


def _init_fyers_ws(client_id: str, access_token: str, symbols: List[str]) -> Any:
    """Internal helper to initialize a new Fyers Data WebSocket."""
    global WS_FEED, LAST_TICK_TIME
    try:
        from fyers_apiv3.FyersWebsocket import data_ws
        
        def on_fyers_message(message):
            global LAST_TICK_TIME
            # Fyers message format: type='sf' for symbol feed
            if isinstance(message, dict) and (message.get("type") == "sf" or "ltp" in message):
                sym = message.get("symbol")
                ltp = message.get("ltp")
                if sym and ltp:
                    # Strip -EQ if present for matching with strategy symbols
                    clean_sym = sym.replace("-EQ", "")
                    LTP_DICT[clean_sym] = float(ltp)
                    LAST_TICK_TIME = time.time()

        def on_fyers_error(message):
            log.error(f"Fyers WS Error: {message}")

        def on_fyers_close(message):
            log.warning(f"Fyers WS Closed: {message}")

        def on_fyers_open():
            log.info("[OK] Fyers WebSocket Connection Opened!")
            try:
                time.sleep(1) # Small delay for stability
                # Subscribe to symbols
                fyers_symbols = [s if "-EQ" in s else f"{s}-EQ" for s in symbols]
                # Also add Nifty 50 Index for testing
                if "NSE:NIFTY50-INDEX" not in fyers_symbols:
                    fyers_symbols.append("NSE:NIFTY50-INDEX")
                
                log.info(f"📡 Subscribing to Fyers symbols: {fyers_symbols}")
                WS_FEED.subscribe(symbols=fyers_symbols, data_type="SymbolUpdate")
                log.info("✅ Subscription command sent successfully")
            except Exception as e:
                log.error(f"❌ Failed to send subscription command: {e}")

        WS_FEED = data_ws.FyersDataSocket(
            access_token=f"{client_id}:{access_token}",
            log_path=os.getcwd(),
            litemode=False,
            on_connect=on_fyers_open,
            on_close=on_fyers_close,
            on_error=on_fyers_error,
            on_message=on_fyers_message
        )
        
        WS_FEED.connect()
        log.info(f"Fyers WebSocket initializing for {len(symbols)} symbols...")
        return WS_FEED

    except Exception as e:
        log.error(f"Failed to initialize Fyers WebSocket: {e}")
        return None

def _init_ws(client_id: str, access_token: str, security_ids: List[str]) -> Any:
    """Internal helper to initialize a new MarketFeed instance."""
    global WS_FEED, LAST_TICK_TIME
    try:
        from dhanhq.marketfeed import MarketFeed
        from dhanhq import DhanContext
        
        context = DhanContext(client_id, access_token)
        # Format for Dhan WebSocket: (Exchange, Security_ID)
        instruments = [(MarketFeed.NSE, str(sec_id)) for sec_id in security_ids]
        
        WS_FEED = MarketFeed(
            context,
            instruments,
            version='v2',
            on_connect=on_connect,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        def run_ws() -> None:
            """Execution loop for the WebSocket thread."""
            global LAST_TICK_TIME
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                LAST_TICK_TIME = time.time() # Reset tick time on new connection attempt
                WS_FEED.run_forever()
            except Exception as e:
                log.error(f"WebSocket thread crashed: {e}")
                
        ws_thread = threading.Thread(target=run_ws, daemon=True)
        ws_thread.name = "WS-Worker-Thread"
        ws_thread.start()
        
        log.info(f"Dhan WebSocket initializing for {len(security_ids)} symbols...")
        return WS_FEED
        
    except Exception as e:
        log.error(f"Failed to initialize Dhan WebSocket: {e}")
        return None

def _connection_monitor() -> None:
    """
    Background thread that monitors the connection health.
    If no ticks are received for 90s during market hours, it triggers a reconnect.
    """
    global LAST_TICK_TIME, WS_FEED
    
    log.info("WebSocket Heartbeat Monitor started.")
    time.sleep(30) # Wait for initial connection stabilization
    
    while True:
        try:
            now = datetime.now()
            # Market hours check (IST 9:15 AM to 3:35 PM)
            is_market_hours = ("09:15" <= now.strftime("%H:%M") <= "15:35")
            is_weekday = (now.weekday() < 5)
            
            if is_market_hours and is_weekday:
                idle_time = time.time() - LAST_TICK_TIME
                if idle_time > 90:
                    log.warning(f"⚠️ WebSocket SILENCE DETECTED ({int(idle_time)}s). Attempting Auto-Reconnect...")
                    
                    if WS_PARAMS:
                        start_websocket(
                            WS_PARAMS['client_id'], 
                            WS_PARAMS['access_token'], 
                            WS_PARAMS['symbols'],
                            WS_PARAMS.get('broker_type', 'dhan')
                        )
                        log.info("♻️ Reconnection command sent.")
                        time.sleep(30) # Cooldown before next check
            
        except Exception as e:
            log.error(f"Heartbeat Monitor Error: {e}")
            
        time.sleep(60)

