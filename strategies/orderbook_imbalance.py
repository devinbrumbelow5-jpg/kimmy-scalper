"""
Kimmy Orderbook Imbalance Strategy
Ultra-low latency scalping using L2 orderbook data
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Dict, List
from decimal import Decimal
import numpy as np


@dataclass
class Signal:
    side: str  # 'buy' | 'sell'
    confidence: float  # 0.0 - 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    timestamp: float


@dataclass
class OrderbookLevel:
    price: float
    volume: float
    timestamp: float


class OrderbookImbalanceStrategy:
    """
    High-frequency scalping strategy using:
    1. Orderbook imbalance (bid/ask ratio)
    2. Momentum bursts (volume + price velocity)
    3. RSI divergence detection
    4. Dynamic position sizing
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.orderbook = {'bids': [], 'asks': []}
        self.recent_trades = []
        self.rsi_values = []
        self.price_history = []
        self.volume_history = []
        
        # Strategy parameters
        self.depth = config.get('orderbook_depth', 10)
        self.imbalance_threshold = config.get('imbalance_threshold', 0.65)
        self.momentum_lookback = config.get('momentum_lookback', 20)
        self.volume_spike = config.get('volume_spike_multiplier', 2.0)
        self.rsi_period = config.get('rsi_period', 14)
        
        # Risk parameters
        self.stop_loss = config.get('stop_loss_initial', 0.005)
        self.take_profit = config.get('take_profit_initial', 0.01)
        self.trailing_activation = config.get('trailing_stop_activation', 0.005)
        self.trailing_distance = config.get('trailing_stop_distance', 0.003)
        
        # State
        self.last_signal_time = 0
        self.signal_cooldown = 5  # seconds between signals
        self.position = None
        
    def update_orderbook(self, bids: List[OrderbookLevel], asks: List[OrderbookLevel]):
        """Update L2 orderbook data"""
        self.orderbook['bids'] = sorted(bids, key=lambda x: x.price, reverse=True)[:self.depth]
        self.orderbook['asks'] = sorted(asks, key=lambda x: x.price)[:self.depth]
        
    def update_trades(self, trades: List[dict]):
        """Update recent trade feed"""
        current_time = time.time()
        self.recent_trades = [t for t in trades if current_time - t['timestamp'] < 60]
        self.recent_trades.extend(trades)
        
        # Update price/volume history
        for trade in trades:
            self.price_history.append(trade['price'])
            self.volume_history.append(trade['volume'])
            
        # Keep history limited
        max_history = self.momentum_lookback * 2
        self.price_history = self.price_history[-max_history:]
        self.volume_history = self.volume_history[-max_history:]
        
    def calculate_imbalance(self) -> float:
        """Calculate bid/ask imbalance ratio (0.0 - 1.0)"""
        if not self.orderbook['bids'] or not self.orderbook['asks']:
            return 0.5
            
        bid_volume = sum(level.volume for level in self.orderbook['bids'])
        ask_volume = sum(level.volume for level in self.orderbook['asks'])
        
        total = bid_volume + ask_volume
        if total == 0:
            return 0.5
            
        return bid_volume / total
        
    def calculate_momentum(self) -> tuple:
        """Calculate price and volume momentum"""
        if len(self.price_history) < self.momentum_lookback:
            return 0.0, 0.0
            
        # Price momentum (% change)
        recent_prices = self.price_history[-self.momentum_lookback:]
        price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        # Volume momentum
        if len(self.volume_history) >= self.momentum_lookback * 2:
            recent_vol = np.mean(self.volume_history[-self.momentum_lookback:])
            prev_vol = np.mean(self.volume_history[-self.momentum_lookback*2:-self.momentum_lookback])
            volume_momentum = recent_vol / prev_vol if prev_vol > 0 else 1.0
        else:
            volume_momentum = 1.0
            
        return price_momentum, volume_momentum
        
    def calculate_rsi(self) -> float:
        """Calculate RSI from price history"""
        if len(self.price_history) < self.rsi_period + 1:
            return 50.0
            
        prices = np.array(self.price_history[-self.rsi_period-1:])
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def get_best_prices(self) -> tuple:
        """Get best bid and ask from orderbook"""
        if not self.orderbook['bids'] or not self.orderbook['asks']:
            return None, None
            
        best_bid = self.orderbook['bids'][0].price
        best_ask = self.orderbook['asks'][0].price
        
        return best_bid, best_ask
        
    def generate_signal(self) -> Optional[Signal]:
        """Generate trading signal based on orderbook and momentum"""
        current_time = time.time()
        
        # Cooldown check
        if current_time - self.last_signal_time < self.signal_cooldown:
            return None
            
        # Need sufficient data
        if not self.orderbook['bids'] or not self.orderbook['asks']:
            return None
            
        # Calculate indicators
        imbalance = self.calculate_imbalance()
        price_momentum, volume_momentum = self.calculate_momentum()
        rsi = self.calculate_rsi()
        
        best_bid, best_ask = self.get_best_prices()
        if best_bid is None:
            return None
            
        mid_price = (best_bid + best_ask) / 2
        
        # Determine signal
        signal = None
        confidence = 0.0
        reason = ""
        
        # LONG signal conditions
        if imbalance > self.imbalance_threshold and volume_momentum > self.volume_spike:
            if price_momentum > 0 and rsi < 70:  # Not overbought
                confidence = min(imbalance * 1.5, 1.0)
                reason = f"Orderbook imbalance: {imbalance:.2%}, Vol spike: {volume_momentum:.2f}x"
                signal = 'buy'
                
        # SHORT signal conditions  
        elif imbalance < (1 - self.imbalance_threshold) and volume_momentum > self.volume_spike:
            if price_momentum < 0 and rsi > 30:  # Not oversold
                confidence = min((1-imbalance) * 1.5, 1.0)
                reason = f"Orderbook imbalance: {imbalance:.2%}, Vol spike: {volume_momentum:.2f}x"
                signal = 'sell'
                
        if signal:
            self.last_signal_time = current_time
            
            # Calculate entry/stop/take-profit
            if signal == 'buy':
                entry = best_ask  # Buy at ask
                stop = entry * (1 - self.stop_loss)
                take = entry * (1 + self.take_profit)
            else:
                entry = best_bid  # Sell at bid
                stop = entry * (1 + self.stop_loss)
                take = entry * (1 - self.take_profit)
                
            return Signal(
                side=signal,
                confidence=confidence,
                entry_price=entry,
                stop_loss=stop,
                take_profit=take,
                reason=reason,
                timestamp=current_time
            )
            
        return None
        
    def should_exit(self, position: dict, current_price: float) -> Optional[str]:
        """Determine if position should be exited (trailing stop, time-based, etc.)"""
        if not position:
            return None
            
        entry = position.get('entry_price')
        side = position.get('side')
        open_time = position.get('open_time', 0)
        
        # Time-based exit (max 5 minutes for scalping)
        if time.time() - open_time > 300:
            return "time_exit"
            
        # Trailing stop
        if side == 'long':
            pnl_pct = (current_price - entry) / entry
            if pnl_pct >= self.trailing_activation:
                trailing_stop = current_price * (1 - self.trailing_distance)
                if current_price <= trailing_stop:
                    return "trailing_stop"
        else:  # short
            pnl_pct = (entry - current_price) / entry
            if pnl_pct >= self.trailing_activation:
                trailing_stop = current_price * (1 + self.trailing_distance)
                if current_price >= trailing_stop:
                    return "trailing_stop"
        
        return None
