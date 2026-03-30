"""
Kimmy Backtester
Backtesting engine for strategy validation
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

import ccxt
from strategies.orderbook_imbalance import OrderbookImbalanceStrategy, Signal

@dataclass
class BacktestResult:
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    avg_trade_return: float
    equity_curve: List[float]
    trades: List[Dict]
    
class KimmyBacktester:
    """
    Walk-forward backtesting engine
    Simulates real trading conditions with:
    - Realistic slippage (5 bps)
    - Taker fees (10 bps)
    - Orderbook lag
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.strategy = OrderbookImbalanceStrategy(config.get('strategy', {}))
        
    def fetch_data(self, pair: str, timeframe: str = '1m', 
                   since_days: int = 90) -> pd.DataFrame:
        """Fetch historical OHLCV data"""
        since = int((datetime.now() - timedelta(days=since_days)).timestamp() * 1000)
        
        print(f"[BACKTEST] Fetching {pair} {timeframe} data (last {since_days} days)...")
        
        ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, since=since)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        print(f"[BACKTEST] Loaded {len(df)} candles")
        return df
        
    def simulate_orderbook(self, row: pd.Series) -> Tuple[List, List]:
        """Generate synthetic L2 orderbook from OHLCV"""
        # Use high/low as bid/ask spread estimate
        mid = (row['high'] + row['low']) / 2
        spread = (row['high'] - row['low']) / mid
        
        # Generate 10 levels on each side
        bids = []
        asks = []
        
        for i in range(10):
            bid_price = mid * (1 - spread * (i + 1) * 0.1)
            ask_price = mid * (1 + spread * (i + 1) * 0.1)
            
            # Volume proportional to inverse of level
            volume = row['volume'] / 20 * (1 - i * 0.08)
            
            bids.append((bid_price, volume))
            asks.append((ask_price, volume))
            
        return bids, asks
        
    def run(self, pair: str, days: int = 90, 
            slippage: float = 0.0005, fees: float = 0.001) -> BacktestResult:
        """
        Run backtest simulation
        
        Returns:
            BacktestResult with full statistics
        """
        # Fetch data
        df = self.fetch_data(pair, '1m', days)
        
        # Initialize
        balance = 1000.0
        initial_balance = balance
        equity = [balance]
        trades = []
        position = None
        
        max_position_size = self.config.get('trading', {}).get('max_position_size', 0.005)
        max_open = self.config.get('trading', {}).get('max_open_positions', 5)
        
        print(f"[BACKTEST] Running simulation on {len(df)} candles...")
        
        # Walk-forward simulation
        for i in range(len(df) - 1):
            row = df.iloc[i]
            next_row = df.iloc[i + 1]
            
            # Simulate orderbook
            bids, asks = self.simulate_orderbook(row)
            
            # Update strategy
            from strategies.orderbook_imbalance import OrderbookLevel
            self.strategy.update_orderbook(
                [OrderbookLevel(p, v, 0) for p, v in bids],
                [OrderbookLevel(p, v, 0) for p, v in asks]
            )
            
            # Add synthetic trades for momentum calculation
            trades_feed = [{'price': row['close'], 'volume': row['volume'], 'timestamp': 0}]
            self.strategy.update_trades(trades_feed)
            
            # Check position exits
            if position:
                exit_price = next_row['open']  # Exit at next candle open
                
                # Apply slippage
                if position['side'] == 'long':
                    exit_price *= (1 - slippage)
                    pnl = (exit_price - position['entry']) / position['entry']
                else:
                    exit_price *= (1 + slippage)
                    pnl = (position['entry'] - exit_price) / position['entry']
                    
                # Apply fees
                pnl -= fees * 2  # Entry + exit fees
                
                # Check stops
                exit_reason = None
                if pnl <= -0.005:
                    exit_reason = 'stop_loss'
                elif pnl >= 0.01:
                    exit_reason = 'take_profit'
                    
                if exit_reason:
                    trade = {
                        'entry': position['entry'],
                        'exit': exit_price,
                        'side': position['side'],
                        'pnl': pnl,
                        'reason': exit_reason
                    }
                    trades.append(trade)
                    balance *= (1 + pnl * max_position_size)
                    equity.append(balance)
                    position = None
                    
            # Check for new entry
            else:
                signal = self.strategy.generate_signal()
                if signal:
                    entry_price = next_row['open']
                    
                    # Apply slippage
                    if signal.side == 'buy':
                        entry_price *= (1 + slippage)
                    else:
                        entry_price *= (1 - slippage)
                        
                    position = {
                        'side': 'long' if signal.side == 'buy' else 'short',
                        'entry': entry_price,
                        'stop': signal.stop_loss,
                        'take': signal.take_profit
                    }
                    
        # Calculate statistics
        if not trades:
            print("[BACKTEST] ⚠️ No trades executed during backtest period")
            return BacktestResult(
                total_trades=0, win_rate=0, profit_factor=0,
                sharpe_ratio=0, max_drawdown=0, total_return=0,
                avg_trade_return=0, equity_curve=equity, trades=[]
            )
            
        # Metrics
        wins = sum(1 for t in trades if t['pnl'] > 0)
        win_rate = wins / len(trades)
        
        avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / max(wins, 1)
        avg_loss = sum(t['pnl'] for t in trades if t['pnl'] <= 0) / max(len(trades) - wins, 1)
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        returns = [t['pnl'] for t in trades]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252 * 24 * 60) if np.std(returns) > 0 else 0
        
        # Max drawdown
        peak = initial_balance
        max_dd = 0
        for bal in equity:
            if bal > peak:
                peak = bal
            dd = (peak - bal) / peak
            max_dd = max(max_dd, dd)
            
        total_return = (balance - initial_balance) / initial_balance
        
        print(f"\n[BACKTEST] Results for {pair}:")
        print(f"  Total Trades: {len(trades)}")
        print(f"  Win Rate: {win_rate:.1%}")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Sharpe Ratio: {sharpe:.2f}")
        print(f"  Max Drawdown: {max_dd:.2%}")
        print(f"  Total Return: {total_return:.2%}")
        print(f"  Avg Trade: {np.mean(returns):.3%}")
        
        return BacktestResult(
            total_trades=len(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_return=total_return,
            avg_trade_return=np.mean(returns),
            equity_curve=equity,
            trades=trades
        )
        
if __name__ == "__main__":
    # Run backtest
    config = {
        'trading': {
            'primary_pair': 'BTC/USDT',
            'max_position_size': 0.005,
            'max_open_positions': 5
        },
        'strategy': {
            'orderbook_depth': 10,
            'imbalance_threshold': 0.65,
            'momentum_lookback': 20,
            'momentum_threshold': 0.001,
            'volume_spike_multiplier': 2.0,
            'rsi_period': 14,
            'stop_loss_initial': 0.005,
            'take_profit_initial': 0.01
        }
    }
    
    bt = KimmyBacktester(config)
    result = bt.run('BTC/USDT', days=30)
