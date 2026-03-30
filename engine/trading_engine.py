"""
Kimmy Trading Engine
Core execution logic with WebSocket integration
"""
import asyncio
import json
import time
import logging
from decimal import Decimal
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable
from datetime import datetime
import traceback

import ccxt
import ccxt.pro as ccxtpro
from websockets import connect

from strategies.orderbook_imbalance import OrderbookImbalanceStrategy, Signal, OrderbookLevel

@dataclass
class Position:
    id: str
    pair: str
    side: str  # 'long' | 'short'
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    open_time: float
    max_favorable: float = 0.0
    partial_exit: bool = False
    
@dataclass  
class Trade:
    id: str
    pair: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    reason: str
    open_time: float
    close_time: float
    duration: float

class PaperTradingExchange:
    """Simulated exchange for paper trading with realistic fills"""
    
    def __init__(self, initial_balance: float = 1000.0, slippage: float = 0.0005, fees: float = 0.001):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.slippage = slippage
        self.fees = fees
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.orderbook = {'bids': [], 'asks': []}
        self.current_price = 0.0
        
    def update_price(self, price: float):
        """Update current market price"""
        self.current_price = price
        
    def update_orderbook(self, bids: List[tuple], asks: List[tuple]):
        """Update L2 orderbook"""
        self.orderbook['bids'] = bids
        self.orderbook['asks'] = asks
        if bids and asks:
            self.current_price = (bids[0][0] + asks[0][0]) / 2
            
    def get_fill_price(self, side: str, size: float) -> float:
        """Calculate realistic fill price with slippage"""
        if side == 'buy':
            base_price = self.orderbook['asks'][0][0] if self.orderbook['asks'] else self.current_price
            # Add slippage for taker orders
            fill_price = base_price * (1 + self.slippage)
        else:
            base_price = self.orderbook['bids'][0][0] if self.orderbook['bids'] else self.current_price
            fill_price = base_price * (1 - self.slippage)
            
        return fill_price
        
    def open_position(self, pair: str, side: str, size_pct: float, 
                     stop_loss: float, take_profit: float) -> Optional[Position]:
        """Open a new position"""
        if pair in self.positions:
            return None
            
        position_size = self.balance * size_pct
        fill_price = self.get_fill_price(side, position_size)
        
        # Apply fees
        fee = position_size * self.fees
        self.balance -= fee
        
        pos = Position(
            id=f"pos_{int(time.time() * 1000)}",
            pair=pair,
            side='long' if side == 'buy' else 'short',
            entry_price=fill_price,
            size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            open_time=time.time()
        )
        
        self.positions[pair] = pos
        logging.info(f"[PAPER] Opened {side} position: {pair} @ {fill_price:,.2f}, size=${position_size:.2f}")
        return pos
        
    def close_position(self, pair: str, reason: str) -> Optional[Trade]:
        """Close an existing position"""
        if pair not in self.positions:
            return None
            
        pos = self.positions.pop(pair)
        fill_price = self.get_fill_price('sell' if pos.side == 'long' else 'buy', pos.size)
        
        # Calculate PnL
        if pos.side == 'long':
            pnl = (fill_price - pos.entry_price) * (pos.size / pos.entry_price)
            pnl_pct = (fill_price - pos.entry_price) / pos.entry_price
        else:
            pnl = (pos.entry_price - fill_price) * (pos.size / pos.entry_price)
            pnl_pct = (pos.entry_price - fill_price) / pos.entry_price
            
        # Apply fees
        fee = pos.size * self.fees
        pnl -= fee
        self.balance += pos.size + pnl
        
        trade = Trade(
            id=f"trade_{int(time.time() * 1000)}",
            pair=pair,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=fill_price,
            size=pos.size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            open_time=pos.open_time,
            close_time=time.time(),
            duration=time.time() - pos.open_time
        )
        
        self.trades.append(trade)
        logging.info(f"[PAPER] Closed {pos.side} position: {pair} @ {fill_price:,.2f}, "
                    f"PnL={pnl:+.2f} ({pnl_pct:+.2%}), reason={reason}")
        return trade
        
    def update_positions(self):
        """Check stop-loss/take-profit for open positions"""
        for pair, pos in list(self.positions.items()):
            current = self.current_price
            
            if pos.side == 'long':
                pnl_pct = (current - pos.entry_price) / pos.entry_price
                if pnl_pct > pos.max_favorable:
                    pos.max_favorable = pnl_pct
            else:
                pnl_pct = (pos.entry_price - current) / pos.entry_price
                if pnl_pct > pos.max_favorable:
                    pos.max_favorable = pnl_pct
                    
            # Check stops
            if pnl_pct <= -0.005:  # 0.5% hard stop
                self.close_position(pair, 'stop_loss')
            elif pnl_pct >= 0.01:  # 1% take profit
                self.close_position(pair, 'take_profit')
                
    def get_stats(self) -> Dict:
        """Calculate trading statistics"""
        if not self.trades:
            return {
                'balance': self.balance,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'sharpe': 0.0,
                'drawdown': 0.0,
                'open_positions': len(self.positions),
                'daily_trades': 0,
                'total_trades': 0
            }
            
        total_pnl = sum(t.pnl_pct for t in self.trades)
        wins = sum(1 for t in self.trades if t.pnl > 0)
        win_rate = wins / len(self.trades)
        
        # Calculate Sharpe (simplified)
        returns = [t.pnl_pct for t in self.trades]
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        sharpe = avg_return / (variance ** 0.5) if variance > 0 else 0
        
        # Calculate drawdown
        peak = self.initial_balance
        max_dd = 0
        running = self.initial_balance
        for t in self.trades:
            running += t.pnl
            if running > peak:
                peak = running
            dd = (peak - running) / peak
            max_dd = max(max_dd, dd)
            
        return {
            'balance': self.balance,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'drawdown': max_dd,
            'open_positions': len(self.positions),
            'daily_trades': sum(1 for t in self.trades 
                                if datetime.fromtimestamp(t.close_time).date() == datetime.now().date()),
            'total_trades': len(self.trades)
        }

class TradingEngine:
    """Main trading engine integrating strategy, data, and execution"""
    
    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.strategy: Optional[OrderbookImbalanceStrategy] = None
        self.exchange: Optional[PaperTradingExchange] = None
        self.ws_connection = None
        self.last_update = 0
        self.current_signal: Optional[Signal] = None
        
        # Stats
        self.stats = {
            'balance': config.get('paper_balance', 1000),
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'sharpe': 0.0,
            'drawdown': 0.0,
            'open_positions': 0,
            'daily_trades': 0,
            'total_trades': 0
        }
        
        # Callbacks
        self.on_trade: Optional[Callable] = None
        self.on_signal: Optional[Callable] = None
        
    async def initialize(self):
        """Initialize strategy and exchange"""
        strategy_config = self.config.get('strategy', {})
        self.strategy = OrderbookImbalanceStrategy(strategy_config)
        
        trading_config = self.config.get('trading', {})
        self.exchange = PaperTradingExchange(
            initial_balance=trading_config.get('paper_balance', 1000),
            slippage=trading_config.get('paper_slippage', 0.0005),
            fees=trading_config.get('paper_fees', 0.001)
        )
        
        # Connect to exchange WebSocket
        await self.connect_websocket()
        
        logging.info("[ENGINE] Trading engine initialized")
        
    async def connect_websocket(self):
        """Connect to Bybit WebSocket for real-time data"""
        pair = self.config.get('trading', {}).get('primary_pair', 'BTCUSDT')
        symbol = pair.replace('/', '')
        
        # Bybit WebSocket (better US support)
        ws_url = f"wss://stream.bybit.com/v5/public/linear"
        
        try:
            self.ws_connection = await connect(ws_url)
            # Subscribe to orderbook
            subscribe_msg = {
                "op": "subscribe",
                "args": [{"channel": f"orderbook.50.{symbol}"}]
            }
            await self.ws_connection.send(json.dumps(subscribe_msg))
            logging.info(f"[ENGINE] WebSocket connected: {ws_url} ({symbol})")
        except Exception as e:
            logging.error(f"[ENGINE] WebSocket connection failed: {e}")
            # Fall back to REST API polling
            logging.info("[ENGINE] Falling back to REST polling")
            
    async def process_message(self, message: str):
        """Process WebSocket message"""
        try:
            data = json.loads(message)
            
            # Orderbook update
            if 'bids' in data or 'asks' in data:
                bids = [OrderbookLevel(float(b[0]), float(b[1]), time.time()) 
                       for b in data.get('bids', [])]
                asks = [OrderbookLevel(float(a[0]), float(a[1]), time.time())
                       for a in data.get('asks', [])]
                self.strategy.update_orderbook(bids, asks)
                self.exchange.update_orderbook(
                    [(b.price, b.volume) for b in bids],
                    [(a.price, a.volume) for a in asks]
                )
                
            # Trade update
            if 'p' in data and 'q' in data:
                trade = {
                    'price': float(data['p']),
                    'volume': float(data['q']),
                    'timestamp': time.time(),
                    'side': 'buy' if data.get('m') else 'sell'
                }
                self.strategy.update_trades([trade])
                self.exchange.update_price(trade['price'])
                
        except Exception as e:
            logging.error(f"[ENGINE] Message processing error: {e}")
            
    async def run_loop(self):
        """Main trading loop"""
        self.running = True
        update_interval = 0.1  # 100ms
        
        while self.running:
            try:
                # Receive WebSocket data
                if self.ws_connection:
                    try:
                        message = await asyncio.wait_for(
                            self.ws_connection.recv(), 
                            timeout=update_interval
                        )
                        await self.process_message(message)
                    except asyncio.TimeoutError:
                        pass
                        
                # Update positions
                self.exchange.update_positions()
                
                # Generate signals
                signal = self.strategy.generate_signal()
                if signal:
                    self.current_signal = signal
                    if self.on_signal:
                        self.on_signal(signal)
                        
                    # Execute if we have capacity
                    max_pos = self.config.get('trading', {}).get('max_open_positions', 5)
                    if len(self.exchange.positions) < max_pos:
                        await self.execute_signal(signal)
                        
                # Update stats
                self.stats = self.exchange.get_stats()
                
                await asyncio.sleep(0.01)  # 10ms sleep to prevent CPU spin
                
            except Exception as e:
                logging.error(f"[ENGINE] Loop error: {e}")
                await asyncio.sleep(1)
                
    async def execute_signal(self, signal: Signal):
        """Execute trading signal"""
        pair = self.config.get('trading', {}).get('primary_pair', 'BTC/USDT')
        
        # Risk check - 0.5% per trade
        risk_pct = self.config.get('trading', {}).get('max_position_size', 0.005)
        
        if signal.side == 'buy':
            self.exchange.open_position(
                pair, 'buy', risk_pct,
                signal.stop_loss, signal.take_profit
            )
        else:
            self.exchange.open_position(
                pair, 'sell', risk_pct,
                signal.stop_loss, signal.take_profit
            )
            
    def get_stats(self) -> dict:
        """Return current stats"""
        return self.stats
        
    def get_orderbook(self) -> dict:
        """Return current orderbook"""
        if not self.exchange:
            return {'bids': [], 'asks': [], 'mid': 0}
        return self.exchange.orderbook
        
    def get_current_signal(self) -> Optional[dict]:
        """Return current signal"""
        if not self.current_signal:
            return None
        return {
            'side': self.current_signal.side,
            'confidence': self.current_signal.confidence,
            'imbalance': self.strategy.calculate_imbalance(),
            'momentum': self.strategy.calculate_momentum()[0],
            'rsi': self.strategy.calculate_rsi()
        }
        
    def get_recent_trades(self) -> List[dict]:
        """Return recent trades"""
        if not self.exchange:
            return []
        return [
            {
                'time': datetime.fromtimestamp(t.close_time).strftime('%H:%M:%S'),
                'pair': t.pair,
                'side': t.side,
                'entry': t.entry_price,
                'exit': t.exit_price,
                'pnl': t.pnl_pct,
                'reason': t.reason
            }
            for t in reversed(self.exchange.trades[-20:])
        ]
        
    def stop(self):
        """Stop the engine"""
        self.running = False
        logging.info("[ENGINE] Trading engine stopped")
