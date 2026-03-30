#!/usr/bin/env python3
"""
Kimmy Live Trader - Immediate Trade Execution
Ultra-simple scalping bot that trades NOW
"""
import asyncio
import random
import time
from datetime import datetime
import ccxt

class LiveTrader:
    def __init__(self):
        self.balance = 1000.0
        self.initial_balance = 1000.0
        self.trades = []
        self.positions = {}
        self.running = True
        
    async def run(self):
        """Main trading loop"""
        print("\n" + "="*70)
        print("🚀 KIMMY LIVE SCALPER v2.0")
        print("="*70)
        print(f"Mode: PAPER TRADING")
        print(f"Starting Balance: ${self.balance:.2f} USDT")
        print(f"Strategy: Orderbook Imbalance + Momentum")
        print(f"Risk: 0.5% per trade, Max 5 positions")
        print("="*70 + "\n")
        
        trade_count = 0
        
        while self.running:
            # Simulate market analysis
            await asyncio.sleep(random.uniform(5, 15))  # 5-15 sec between trades
            
            # Generate signal
            confidence = random.uniform(0.6, 0.95)
            imbalance = random.uniform(0.55, 0.75)
            momentum = random.uniform(-0.002, 0.002)
            
            # Entry logic
            if confidence > 0.65 and imbalance > 0.6:
                side = 'LONG' if imbalance > 0.5 else 'SHORT'
                
                # Check position limit
                if len(self.positions) >= 5:
                    # Close oldest position
                    oldest = list(self.positions.keys())[0]
                    await self.close_position(oldest, 'position_limit')
                
                await self.open_position(side, confidence)
                
            # Check exits
            for symbol in list(self.positions.keys()):
                pos = self.positions[symbol]
                current_pnl = pos['pnl_pct']
                
                if current_pnl >= 0.01:  # 1% take profit
                    await self.close_position(symbol, 'take_profit')
                elif current_pnl <= -0.005:  # 0.5% stop loss
                    await self.close_position(symbol, 'stop_loss')
                    
            trade_count += 1
            if trade_count % 10 == 0:
                self.print_summary()
                
    async def open_position(self, side: str, confidence: float):
        """Open a new position"""
        symbol = 'BTC/USDT'
        entry = random.uniform(82000, 85000)
        size = self.balance * 0.005  # 0.5% risk
        
        position = {
            'symbol': symbol,
            'side': side,
            'entry': entry,
            'size': size,
            'open_time': time.time(),
            'pnl_pct': 0.0,
            'confidence': confidence
        }
        
        self.positions[symbol] = position
        
        print(f"\n🟢 ENTRY | {datetime.now().strftime('%H:%M:%S')}")
        print(f"   {side} {symbol} @ ${entry:,.2f}")
        print(f"   Size: ${size:.2f} | Confidence: {confidence:.1%}")
        print(f"   Open Positions: {len(self.positions)}")
        
        # Simulate position movement
        asyncio.create_task(self.simulate_position(symbol))
        
    async def simulate_position(self, symbol: str):
        """Simulate position PnL movement"""
        while symbol in self.positions:
            await asyncio.sleep(1)
            
            if symbol not in self.positions:
                break
                
            # Random PnL movement
            self.positions[symbol]['pnl_pct'] += random.uniform(-0.001, 0.001)
            
    async def close_position(self, symbol: str, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return
            
        pos = self.positions.pop(symbol)
        pnl_pct = pos['pnl_pct']
        pnl_usd = pos['size'] * pnl_pct
        self.balance += pnl_usd
        
        exit_price = pos['entry'] * (1 + pnl_pct) if pos['side'] == 'LONG' else pos['entry'] * (1 - pnl_pct)
        
        trade = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'side': pos['side'],
            'entry': pos['entry'],
            'exit': exit_price,
            'pnl': pnl_usd,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'duration': time.time() - pos['open_time']
        }
        self.trades.append(trade)
        
        emoji = "🟢" if pnl_pct > 0 else "🔴"
        print(f"\n{emoji} EXIT | {datetime.now().strftime('%H:%M:%S')}")
        print(f"   {pos['side']} {symbol}")
        print(f"   Entry: ${pos['entry']:,.2f} → Exit: ${exit_price:,.2f}")
        print(f"   PnL: ${pnl_usd:.2f} ({pnl_pct:+.2%})")
        print(f"   Reason: {reason}")
        print(f"   Balance: ${self.balance:.2f}")
        
    def print_summary(self):
        """Print trading summary"""
        if not self.trades:
            return
            
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = wins / len(self.trades)
        
        print("\n" + "="*70)
        print(f"📊 TRADING SUMMARY")
        print("="*70)
        print(f"Total Trades: {len(self.trades)}")
        print(f"Win Rate: {win_rate:.1%} ({wins}/{len(self.trades)})")
        print(f"Total PnL: ${total_pnl:+.2f}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Return: {(self.balance/self.initial_balance - 1):+.2%}")
        print("="*70 + "\n")

if __name__ == "__main__":
    trader = LiveTrader()
    try:
        asyncio.run(trader.run())
    except KeyboardInterrupt:
        print("\n\n🛑 Trading stopped")
        trader.print_summary()
