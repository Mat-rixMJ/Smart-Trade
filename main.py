import time
import logging
from core.ws_manager import WSManager
from core.risk_manager import RiskManager
from strategy.strategy_template import generate_signals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExecutionEngine")

def main():
    logger.info("Starting execution engine...")
    ws = WSManager()
    risk = RiskManager()
    
    try:
        ws.connect()
        while True:
            # Main event loop
            ticks = ws.get_latest_ticks()
            if ticks:
                signals = generate_signals(ticks)
                for signal in signals:
                    if risk.check_risk(signal):
                        logger.info(f"Executing trade: {signal}")
                        # execute_trade(signal)
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        ws.disconnect()

if __name__ == "__main__":
    main()
