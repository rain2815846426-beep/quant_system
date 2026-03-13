
# System Architecture

Data Layer
    ↓
Database Layer
    ↓
Factor Research
    ↓
Machine Learning Models
    ↓
Strategy Engine
    ↓
Backtesting Engine
    ↓
Dashboard Visualization

Core modules:

src/data_fetch
    Stock market data collection (Akshare)

src/data_process
    Data cleaning and alignment

src/factors
    Quant factor calculations

src/models
    ML / DL models

src/backtest
    Backtesting engine

src/strategy
    Portfolio construction

dashboard
    Streamlit UI
