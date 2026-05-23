# Real-Time Algorithmic Trading & ETL Analytics Platform

[![Live Demo](https://img.shields.io/badge/Live_Demo-Interactive_Dashboard-6366F1?style=for-the-badge&logo=streamlit)](http://15.134.152.37/viewer)

An automated quantitative trading and analytics platform built using Python, Fyers API, SQLite (WAL), and Streamlit. The system performs real-time market data extraction via WebSockets, dynamic market regime classification, technical indicator transformation, signal generation, live trade execution with strict risk management, and portfolio analytics through a modular ETL pipeline architecture.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion Layer [Extract]
        WS[WebSockets Manager] -->|Raw Tick Stream| Queue(In-Memory LTP Cache)
        YF[YFinance Integration] -->|Historical Ref Data| DB
    end

    subgraph Analytical Core [Transform]
        Main[Execution Engine] -->|Polls LTP| Queue
        Main -->|Gap & Volatility Metrics| Regime[Regime Classifier]
        Main -->|Vectorized Indicators| Strategy[Signal Generator]
        Main -->|Risk Sizing & Slippage Models| Risk[Risk Manager]
    end

    subgraph Persistence Layer [Load]
        Risk -->|Log Trades / Read Vault State| DB[(SQLite - WAL Mode)]
        Main -->|Write JSON System States| Cache[System State JSON]
    end

    subgraph Presentation & Web Layer
        Dash[Streamlit Dashboards] -->|Read Metrics| DB
        Dash -->|Read System States| Cache
        Nginx[Nginx Reverse Proxy] -->|Secures & Proxies| Dash
    end
```

---

## ✨ Features

- Real-time market data extraction via WebSockets (Fyers API)
- Automated ETL workflow for live tick data processing
- Vectorized technical indicator calculation (VWAP, EMA, MACD, RSI, ATR)
- Dynamic market regime classification (Trending vs. Choppy)
- Signal generation with multi-indicator confluence filters
- Live trade execution with programmatic risk sizing and trailing stop-losses
- Trade logging & PnL tracking in high-concurrency SQLite database
- Interactive Streamlit analytics and presentation dashboard
- Modular Python architecture with decoupled background services
- Automated exception recovery, Telegram alerts, and Email PnL reports

---

## 🛠️ Tech Stack

- **Language:** Python
- **APIs:** Fyers API, YFinance
- **Database:** SQLite (Write-Ahead Logging mode)
- **Data Processing:** Pandas, NumPy
- **Visualization:** Streamlit, Plotly
- **Infrastructure:** AWS EC2, Ubuntu systemd, Nginx

---

## 🔄 Workflow

1. **Fetch** real-time tick data via WebSockets from the broker API.
2. **Clean and cache** raw market data into an in-memory queue.
3. **Classify** the morning market regime using statistical Gap & Range analysis.
4. **Calculate** technical indicators (VWAP, EMA, MACD) via vectorized operations.
5. **Generate** trading signals based on strict multi-indicator confluence rules.
6. **Execute** trades applying dynamic 1.5% risk sizing and trailing stop-losses.
7. **Store** processed data and transaction logs into the SQLite database.
8. **Visualize** real-time analytics and portfolio risk metrics through the decoupled Streamlit dashboard.

---

## 📸 Dashboard Analytics

[![Algodhan Live Quantitative Performance Dashboard Preview](dashboard_preview.png)](http://15.134.152.37/viewer)

*(Click the image above or visit [http://15.134.152.37/viewer](http://15.134.152.37/viewer) to view the live, interactive presentation-grade performance dashboard.)*

---

## 📂 Folder Structure

```text
algodhan-platform/
│
├── logs/                    # SQLite Trade Ledger and JSON state
├── config.py                # System Configuration & Risk Parameters
├── main.py                  # Main Execution Engine & State Controller
├── ws_manager.py            # Asynchronous WebSockets Tick Stream Manager
├── regime_detector.py       # Morning Statistical Market Classifier
├── strategy_pro.py          # Quantitative Indicator Math (EMA, RSI, ADX, ATR)
├── risk_manager.py          # Trade Execution & Position Sizing Logic
├── broker_fyers.py          # Abstracted Broker Client Interface
├── hyper_optimizer.py       # Multi-core Parallel Grid Search Optimizer
├── dashboard.py             # Streamlit Internal Analytical Admin UI
└── public_dashboard.py      # Presentation-Grade Public Performance Viewer
```

---

## 📈 Trading Strategy

The bot uses a sophisticated multi-timeframe, intraday momentum scalping strategy called **VWAP Pullback Scalper v7 ("Institutional Tide")**. It targets high-liquidity Nifty 50 stocks using a confluence of 7 distinct filters:

- **Trend Alignment:** Price must be positioned favorably relative to the 20 EMA and VWAP.
- **Regime Filter:** Underlying index trend and volatility must validate the direction.
- **Volume Spike:** Entry candles must exhibit volume > 1.5x of the 20-period volume SMA.
- **Momentum:** MACD histogram must be expanding in the trade direction.
- **Risk Management:** 
  - Dynamic stop-loss placed at swing extremes or 1.5x ATR.
  - Partial profit booking (TP1) at 1:1 Risk-Reward to lock in gains and trail SL to breakeven.
  - Multi-step trailing stop-loss for trend riding.
  - Hard time-exit at 15:15 IST.

---

## ⚙️ Engineering Highlights

- **Modular ETL Architecture:** Designed a pipeline to automate market data ingestion, transformation, and signal generation while strictly separating data processing from trade execution logic.
- **High-Concurrency Persistence:** Configured SQLite with Write-Ahead Logging (WAL) mode and `synchronous=NORMAL` to allow the trading engine to write high-frequency transaction logs without locking out frontend dashboard reads.
- **Vectorized Operations:** Replaced standard Python loops with Pandas and NumPy vectorization to process hours of 5-minute time-series logs in milliseconds, eliminating computational lag during live execution.
- **Parallel Grid Search:** Utilized Python’s `multiprocessing.Pool` to bypass the Global Interpreter Lock (GIL), distributing parameter optimization calculations across all available AWS CPU cores.
- **Decoupled Visualization:** Built the Streamlit dashboards as isolated reader processes, ensuring UI computations (like Sharpe Ratio and Drawdown) never block the critical execution loop.
- **Resiliency:** Implemented automated connection-recovery mechanisms for WebSockets, daily drawdown kill switches, and systemd daemon management for unattended AWS deployment.

---

## 🚀 Future Improvements

- **Ingestion Message Broker:** Integrate Apache Kafka or RabbitMQ to decouple tick data ingestion from processing.
- **Time-Series Database:** Migrate tick logs to TimescaleDB or ClickHouse for optimized OLAP data querying at scale.
- **API Interface:** Implement a FastAPI web service to serve data endpoints and handle authentication tokens.
- **Frontend Client:** Rebuild the Streamlit dashboard in React.js / Next.js to prevent script-reload bottlenecks.
- **Machine Learning Integration:** Train an XGBoost model on the `logs/` data for predictive regime classification.

---

## 💻 Installation & Usage

**1. Clone and Install Dependencies:**
```bash
git clone https://github.com/yourusername/algodhan-platform.git
cd algodhan-platform
pip install -r requirements.txt
```

**2. Configure Environment:**
Create a `.env` file with your broker credentials:
```env
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key
FYERS_REDIRECT_URI=your_redirect_uri
```

**3. Run the Execution Engine:**
```bash
python main.py
```

**4. Run the Analytics Dashboard:**
```bash
# Internal Admin Dashboard
streamlit run dashboard.py --server.port 8501

# Public Presentation Viewer
streamlit run public_dashboard.py --server.port 8502
```

---

## 🎥 Demo Video

*[Insert link to a short 2-minute Loom or YouTube video demonstrating the live system and dashboard here]*
