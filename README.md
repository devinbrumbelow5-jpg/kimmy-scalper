# 🚀 Kimmy Scalper v2.0

**Elite Ultra-Low Latency Crypto Trading Bot**

Professional-grade high-frequency scalping system with real-time WebSocket feeds, orderbook imbalance detection, and beautiful terminal UI.

---

## Features

### Strategy
- **Orderbook Imbalance Detection** - L2 depth analysis for directional signals
- **Momentum Burst Capture** - Volume + price velocity detection
- **RSI Divergence** - Mean reversion signals
- **Dynamic Position Sizing** - 0.5% risk per trade, max 5 positions
- **Smart Exits** - Trailing stops, partial fills, orderbook reversals

### Execution
- **Real-time WebSocket** - Binance/Bybit direct feeds (<100ms latency)
- **Paper Trading Mode** - Realistic slippage and fee simulation
- **Live Trading Ready** - Toggle after 48h profitable paper trading
- **Auto-restart** - Systemd service with crash recovery

### Monitoring
- **Textual Dashboard** - Professional terminal UI with 2s refresh
- **Live P/L Chart** - Real-time equity curve
- **Orderbook Visualization** - L2 depth display
- **Trade History** - Recent executions with PnL
- **Strategy Signals** - Buy/sell arrows with confidence

---

## Quick Start

```bash
# 1. Install dependencies
python3 setup.py

# 2. Configure API keys (for live mode)
cp config/api_keys.env.example config/api_keys.env
nano config/api_keys.env

# 3. Run paper trading
python3 main.py --paper

# 4. Or with UI
cd ui && python3 dashboard.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  KIMMY SCALPER ARCHITECTURE                          │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────┐      ┌─────────────┐              │
│  │  Exchange   │      │  WebSocket  │              │
│  │  (Binance)  │◄────►│   Feed      │              │
│  └──────┬──────┘      └─────────────┘              │
│         │                                            │
│  ┌──────▼────────┐    ┌─────────────┐              │
│  │ TradingEngine │───►│  Strategy   │              │
│  │               │    │ (Orderbook  │              │
│  │  - Position   │    │ Imbalance)  │              │
│  │  - Risk Mgmt  │    └─────────────┘              │
│  │  - Execution  │                                 │
│  └──────┬────────┘                                 │
│         │                                            │
│  ┌──────▼────────┐    ┌─────────────┐              │
│  │  Paper/Live   │───►│   Textual   │              │
│  │   Exchange    │    │   Dashboard │              │
│  └───────────────┘    └─────────────┘              │
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

## Configuration

Edit `config/config.yaml`:

```yaml
bot:
  mode: "paper"  # paper | live
  
trading:
  primary_pair: "BTC/USDT"
  paper_balance: 1000
  max_position_size: 0.005  # 0.5%
  max_open_positions: 5
  
strategy:
  imbalance_threshold: 0.65  # 65% bid/ask ratio
  momentum_lookback: 20       # 20 seconds
  stop_loss_initial: 0.005    # 0.5%
  take_profit_initial: 0.01   # 1%
```

---

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Win Rate | >60% | 🔄 Testing |
| Sharpe Ratio | >1.5 | 🔄 Testing |
| Max Drawdown | <8% | 🔄 Testing |
| Latency | <100ms | ✅ Active |
| Avg Trade | 30s-5min | 🔄 Testing |

---

## Commands

```bash
# Paper trading (default)
python3 main.py --paper

# Live trading (requires confirmation)
python3 main.py --live

# Headless mode
python3 main.py --paper --headless

# Run as service
sudo systemctl start kimmy-scalper

# View logs
sudo journalctl -u kimmy-scalper -f

# Backtest
python3 backtest/backtester.py
```

---

## Safety

- **Dry-run default** - Never executes real trades unless `--live`
- **Position limits** - Max 0.5% risk per trade, 5 positions total
- **Auto-pause** - Stops on volatility spikes or API errors
- **Emergency kill** - `systemctl stop kimmy-scalper`

---

## Directory Structure

```
KIMMY_SCALPER/
├── config/
│   ├── config.yaml           # Main configuration
│   └── api_keys.env          # API credentials (gitignored)
├── strategies/
│   └── orderbook_imbalance.py  # Core strategy
├── engine/
│   └── trading_engine.py     # Execution logic
├── ui/
│   └── dashboard.py          # Textual interface
├── backtest/
│   └── backtester.py         # Backtesting engine
├── data/                     # Downloaded market data
├── logs/                     # Trading logs
├── setup.py                  # Installation script
├── main.py                   # Entry point
└── run.sh                    # Quick launcher
```

---

## License

MIT - For educational purposes. Trading involves significant risk.

---

**Built by Kimmy - Elite Crypto Scalping Architect**
