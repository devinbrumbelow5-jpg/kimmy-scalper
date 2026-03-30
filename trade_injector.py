#!/usr/bin/env python3
"""
Kimmy Trade Injector - Force trades for testing
"""
import asyncio
import random
import time
from datetime import datetime

# Simulate the trading engine injecting trades
async def force_trades():
    """Force trade execution for testing"""
    print("🚀 KIMMY TRADE INJECTOR")
    print("Forcing trades every 10-30 seconds...\n")
    
    trade_count = 0
    wins = 0
    losses = 0
    balance = 1000.0
    
    while True:
        # Random trade interval
        wait = random.uniform(10, 30)
        await asyncio.sleep(wait)
        
        # Generate trade
        trade_count += 1
        is_win = random.random() > 0.4  # 60% win rate
        
        if is_win:
            pnl = random.uniform(0.005, 0.02)  # 0.5-2% win
            wins += 1
        else:
            pnl = random.uniform(-0.01, -0.005)  # 0.5-1% loss
            losses += 1
            
        trade_value = balance * 0.005  # 0.5% position
        profit = trade_value * pnl
        balance += profit
        
        side = random.choice(['LONG', 'SHORT'])
        entry = random.uniform(82000, 85000)
        exit_price = entry * (1 + pnl) if side == 'LONG' else entry * (1 - pnl)
        
        # Print trade
        print(f"\n{'='*60}")
        print(f"🎯 TRADE #{trade_count} | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"  Side:     {side}")
        print(f"  Entry:    ${entry:,.2f}")
        print(f"  Exit:     ${exit_price:,.2f}")
        print(f"  Size:     ${trade_value:.2f}")
        print(f"  PnL:      ${profit:.2f} ({pnl:+.2%})")
        print(f"  Balance:  ${balance:.2f}")
        print(f"  Win Rate: {wins}/{trade_count} ({wins/trade_count:.1%})")
        
        if balance > 1100:
            print(f"\n🎉 PROFIT TARGET REACHED! +{(balance-1000)/1000:.1%}")
            break
            
        if balance < 950:
            print(f"\n⚠️  DRAWDOWN WARNING: {(balance-1000)/1000:.1%}")

if __name__ == "__main__":
    try:
        asyncio.run(force_trades())
    except KeyboardInterrupt:
        print("\n\nTrade injector stopped.")
