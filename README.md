# Quant ETL Pipeline (Smart-Trade Showcase)

<p align="center">
  <img src="https://raw.githubusercontent.com/Mat-rixMJ/Smart-Trade-/main/dashboard_preview.png" alt="Algodhan Platform Dashboard Mockup" width="800" style="border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0,0,0,0.5);"/>
</p>

<p align="center">
  <a href="http://15.134.152.37/viewer"><img src="https://img.shields.io/badge/Live_Demo-smtrade.space-6366F1?style=for-the-badge&logo=streamlit" alt="Live Demo"/></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python Version"/></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/></a>
  <a href="https://github.com/Mat-rixMJ/Smart-Trade-/stargazers"><img src="https://img.shields.io/github/stars/Mat-rixMJ/Smart-Trade-?style=for-the-badge" alt="GitHub Stars"/></a>
  <a href="https://github.com/Mat-rixMJ/Smart-Trade-/commits/main"><img src="https://img.shields.io/github/last-commit/Mat-rixMJ/Smart-Trade-?style=for-the-badge" alt="Last Commit"/></a>
</p>

---

> [!IMPORTANT]  
> **Repository Notice (Showcase Version)**  
> This is a sanitized, public-facing structural showcase repository. To protect proprietary trading edges, live API keys, and production databases, the core predictive logic and live broker execution components have been abstracted into design templates. The complete, fully operational trading system resides in a private repository.

### Tagline
Production-grade algorithmic trading platform architecture and modular ETL analytics pipeline executing high-probability breakout strategies on NSE equities.

### Description
Algodhan is an automated quantitative trading and analytics platform architecture built in Python, integrating the Fyers API (WebSocket & Order management), SQLite in Write-Ahead Logging (WAL) mode, and Streamlit dashboard visualizers. The platform architecture showcases ingestion of real-time market data, dynamic market regime classification (trending vs. choppy), and compute-intensive technical indicator pipelines. The project exhibits robust systems engineering, clean ETL separation, multi-process daemon configuration, and automated crash-recovery triggers.

### Deployed Live Viewer
👉 **[http://smtrade.space](http://15.134.152.37/viewer/)** *(Interactive Presentation-Grade Performance Dashboard)*

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Showcase Structure Explored](#-showcase-structure-explored)
3. [System Architecture](#-system-architecture)
4. [Tech Stack](#-tech-stack)
5. [Strategy Overview](#-strategy-overview)
6. [Backtesting Results](#-backtesting-results)
7. [Running the Sandbox locally](#-running-the-sandbox-locally)
8. [Environment Variables](#-environment-variables)
9. [Project Structure](#-project-structure)
10. [Roadmap](#-roadmap)
11. [Disclaimer](#-disclaimer)
12. [Author](#-author)
13. [License](#-license)

---

## ⚡ Key Features

- 📡 **Real-Time Data Ingestion Flow**: Asynchronous multi-instrument tick data handler design using WebSockets (abstracted client wrapper in `core/ws_manager.py`).
- 🧠 **Regime Classification Mechanics**: Evaluates volatility, ADX, and Choppiness index trends to calibrate target rewards or sit out of choppy sideways markets.
- 📈 **Modular Data Pipeline**: Decoupled structures computing EMA, RSI, ADX, ATR, VWAP, and daily Pivot Points using Pandas, NumPy, and pandas-ta.
- 🛡️ **Intraday Strategy Template**: Clean layout illustrating a multi-timeframe pullback scalping system, featuring resampled timeframes and confluence checks.
- 💼 **Position Sizing and Risk Sizing**: Structural models illustrating 1.5% capital-at-risk position adjustments, trailing stops, and break-even rules.
- 🗄️ **High-Concurrency SQLite Integration**: SQLite database connection settings utilizing WAL mode and `synchronous=NORMAL` to showcase high-throughput read/write concurrency.
- 📊 **Streamlit Visual Dashboard**: A read-only presentation-grade performance visualizer utilizing Plotly charts, heatmaps, and Sharpe/drawdown metric indicators.

---

## 🔍 Showcase Structure Explored

You are welcome to explore the systems engineering, ETL pipelines, and architecture patterns:
- **Data Ingestion**: Check out [core/ws_manager.py](core/ws_manager.py) to view how asynchronous WebSocket ticks are handled.
- **Risk Engine**: Review [core/risk_manager.py](core/risk_manager.py) to inspect how capital metrics, position sizes, and SQLite WAL settings are configured.
- **UI & Analytics**: Review [dashboard/public_dashboard.py](dashboard/public_dashboard.py) to inspect the premium presentation-grade UI.
- **Deployment Templates**: Review the [docs/](docs/) folder for samples of systemd service daemons and Nginx reverse proxy configurations.

---

## 🏗️ System Architecture

```text
                  +-------------------------------------------------+
                  |                INGESTION LAYER                  |
                  |  [WebSockets Manager]      [YFinance API]       |
                  |   (Real-time LTP ticks)   (Historical Bars)     |
                  +-----------+-----------------------+-------------+
                              |                       |
                              v                       v
                  +-------------------------------------------------+
                  |                 ANALYTICAL CORE                 |
                  |                [Execution Engine]               |
                  |                       |                         |
                  |     +-----------------+-----------------+       |
                  |     |                                   |       |
                  |     v                                   v       |
                  |  [Regime Detector]             [Signal Generator]|
                  |  (Gap & Volatility analysis)   (EMA, RSI, MACD,  |
                  |  (Trending vs. Choppy index)    VWAP, Pivots)   |
                  |     |                                   |       |
                  |     +-----------------+-----------------+       |
                  |                       |                         |
                  |                       v                         |
                  |                [Risk Manager]                   |
                  |           (1.5% Sizing, Trailing SL)            |
                  +-----------------------+-------------------------+
                                          |
                                          v
                  +-------------------------------------------------+
                  |                PERSISTENCE LAYER                |
                  |   [SQLite Database]       [State File Cache]    |
                  |     (WAL Mode Log)          (system_state.json) |
                  +-----------+-----------------------+-------------+
                              |                       |
                              +-----------+-----------+
                                          |
                                          v
                  +-------------------------------------------------+
                  |               PRESENTATION LAYER                |
                  |             [Public Viewer UI]                  |
                  |                 (Port 8502)                     |
                  |                       ^                         |
                  |                       |                         |
                  |             [Nginx Reverse Proxy]               |
                  |                  (Port 80/443)                  |
                  +-------------------------------------------------+
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core application logic and execution engine |
| **Data Ingestion** | Fyers WebSocket API / yfinance | Real-time LTP tick stream ingestion and fallback historical data fetching |
| **Data Processing** | Pandas, NumPy, pandas-ta | Vectorized technical indicators, resampling, and regime analysis |
| **Database** | SQLite (WAL Mode) | High-concurrency trade ledger logging and state persistence |
| **Dashboard** | Streamlit, Plotly | Live admin control panel and read-only interactive analytics dashboard |
| **Deployment** | AWS EC2 (Ubuntu 22.04 LTS) | 24/7 cloud hosting with low-latency network connectivity |
| **Process Control**| Systemd | Deploys execution loops and dashboards as background service daemons |
| **Security/Web** | Nginx | Reverse proxy for Streamlit dashboards, SSL, and network isolation |
| **Notifications** | Telegram Bot API, SMTP | Live crash warnings, trade executions, and end-of-day reports |

---

## 📈 Strategy Overview

The conceptual strategy template (**VWAP Pullback Scalper**) is built around a confluence of multiple technical criteria:
- **Trend Filters**: Verification of price position relative to shorter-term EMAs and anchored Session VWAP.
- **Regime Classification**: Exiting entries or switching criteria dynamically based on the Choppiness Index value.
- **Volume & Momentum confluences**: Volume filters combined with MACD acceleration curves.
- **Support & Resistance**: Pivot point (Daily P, S1, R1) checks.

---

## 📊 Backtesting Results

Simulated testing runs from the core engine across historical benchmark periods:

| Regime | Period | Total Trades | Win Rate | Profit Factor | Max Drawdown | Pass / Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Crash 2020** | 1 Year | 3,713 | 41.3% | 0.54 | 14.9% | ❌ Fail (Unoptimized) |
| **Bull 2021** | 1 Year | 3,555 | 39.2% | 0.39 | 15.8% | ❌ Fail (Unoptimized) |
| **Bear 2022** | 1 Year | 3,724 | 42.1% | 0.42 | 13.7% | ❌ Fail (Unoptimized) |
| **Sideways 2023**| 1 Year | 4,261 | 37.7% | 0.28 | 19.2% | ❌ Fail (Unoptimized) |

> [!NOTE]
> Backtesting results above represent raw unoptimized tests across historical benchmarks. Core strategy parameters are private and optimized dynamically on the server. Contact for collaboration.

---

## 💻 Running the Sandbox Locally

You can run the public Streamlit dashboard in a sandbox state populated with mock trades:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Mat-rixMJ/Smart-Trade-.git
   cd Smart-Trade-
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Settings**:
   ```bash
   cp .env.example .env
   ```

4. **Populate Sandbox Data**:
   Generate mock trade records to populate the SQLite database:
   ```bash
   python dashboard/populate_data.py
   ```

5. **Launch the Dashboard**:
   ```bash
   streamlit run dashboard/public_dashboard.py
   ```
   Open `http://localhost:8501/` to explore the presentation UI.

---

## ⚙️ Environment Variables

| Variable | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `DHAN_CLIENT_ID` | Client ID for Dhan API integration | No | - |
| `DHAN_ACCESS_TOKEN` | Personal Access Token for Dhan API | No | - |
| `FYERS_CLIENT_ID` | App ID / Client ID for Fyers API | Yes (if Fyers) | - |
| `FYERS_SECRET_KEY` | App Secret Key for Fyers API | Yes (if Fyers) | - |
| `FYERS_REDIRECT_URI` | Redirect URL registered in Fyers Dashboard | Yes | `http://127.0.0.1:5000/` |
| `TELEGRAM_BOT_TOKEN` | Token for Telegram notification bot | Yes | - |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for logs and alerts receiver | Yes | - |
| `EMAIL_SENDER` | SMTP sender gmail address | Yes | - |
| `EMAIL_RECEIVER` | Destination email for daily trade reports | Yes | - |
| `EMAIL_APP_PASSWORD` | App-specific Google password for SMTP auth | Yes | - |

---

## 📂 Project Structure

```text
Smart-Trade-/
├── .env.example              # Template for API credentials and settings
├── .gitignore                # Git ignore configuration
├── requirements.txt          # Python dependencies list
├── config.py                 # System configuration and settings
├── main.py                   # Simplified execution engine bootstrap
├── core/
│   ├── ws_manager.py         # Asynchronous WebSocket listener for tick streaming
│   ├── regime_detector.py    # Gap & Volatility morning market regime classifier
│   ├── risk_manager.py       # Positions sizing, database logging, and risk controls
│   └── notifier.py           # Alert manager for Telegram updates and daily report emails
├── strategy/
│   ├── strategy_template.py  # Abstracted layout strategy model for user implementation
│   └── exchange.py           # Multi-exchange utility helper
├── dashboard/
│   ├── public_dashboard.py   # Streamlit public visual dashboard viewer
│   └── populate_data.py      # Seed database generator for sandbox simulation
└── docs/
    ├── Nginx_setup.conf      # Sample reverse-proxy gateway routing configuration
    └── systemd_setup.service # Sample systemd service process control configuration
```

---

## 🚀 Roadmap

- [ ] **Sanitized Backtester Sandbox**: Standardize a backtest script utilizing historical csv datasets for local sandbox tests.
- [ ] **Advanced Indicators Extension**: Incorporate standard Bollinger Band and MACD histogram metrics inside the strategy template.
- [ ] **React.js Dashboard Version**: Re-architecture the frontend visualizer into a clean modern dashboard template using Next.js.

---

## ⚠️ Disclaimer

This software is for educational purposes only. Trading financial instruments involves high risk, and you may lose more than your initial capital. The author is not a SEBI-registered financial advisor, and this platform does not constitute investment advice. Perform your own due diligence before deploying real capital.

---

## 👤 Author

**Manoj Kumar**
- **GitHub**: [Mat-rixMJ](https://github.com/Mat-rixMJ)
- **LinkedIn**: [Manoj Kumar](https://www.linkedin.com/in/manoj-kumar-algotrader)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
