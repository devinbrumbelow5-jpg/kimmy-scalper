#!/usr/bin/env python3
"""
Kimmy Scalper - Main Entry Point
Ultra-Low Latency Crypto Trading Bot
"""
import asyncio
import argparse
import logging
import sys
import signal
import yaml
from pathlib import Path
from datetime import datetime

from engine.trading_engine import TradingEngine
try:
    from ui.dashboard import KimmyDashboard
    HAS_TEXTUAL = True
except ImportError:
    from ui.simple_dashboard import SimpleDashboard
    HAS_TEXTUAL = False

def setup_logging(config: dict):
    """Configure structured logging"""
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_config.get('file'):
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_config['file'],
            maxBytes=log_config.get('max_size_mb', 100) * 1024 * 1024,
            backupCount=log_config.get('backup_count', 5)
        )
        handlers.append(file_handler)
        
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger('kimmy')

class KimmyBot:
    """Main bot orchestrator"""
    
    def __init__(self, config_path: str, paper: bool = True):
        self.config_path = config_path
        self.paper_mode = paper
        self.config = self.load_config()
        self.engine: TradingEngine = None
        self.dashboard: KimmyDashboard = None
        self.logger = None
        self.running = False
        
    def load_config(self) -> dict:
        """Load configuration from YAML"""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Override mode
        config['bot']['mode'] = 'paper' if self.paper_mode else 'live'
        
        return config
        
    async def start(self):
        """Start the bot"""
        self.logger = setup_logging(self.config)
        self.logger.info("="*60)
        self.logger.info("🚀 KIMMY SCALPER v2.0 - ELITE CRYPTO TRADING")
        self.logger.info("="*60)
        self.logger.info(f"Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        self.logger.info(f"Pair: {self.config['trading']['primary_pair']}")
        self.logger.info(f"Balance: ${self.config['trading']['paper_balance']} USDT")
        self.logger.info("="*60)
        
        # Initialize trading engine
        self.engine = TradingEngine(self.config)
        await self.engine.initialize()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start UI if enabled
        if self.config.get('ui', {}).get('enabled', True):
            if HAS_TEXTUAL:
                self.dashboard = KimmyDashboard(self.engine)
            else:
                self.dashboard = SimpleDashboard(self.engine)
                
            # Run UI in separate task
            if HAS_TEXTUAL:
                ui_task = asyncio.create_task(self._run_ui())
            else:
                ui_task = asyncio.create_task(self.dashboard.run())
            engine_task = asyncio.create_task(self.engine.run_loop())
            
            try:
                await asyncio.gather(ui_task, engine_task)
            except asyncio.CancelledError:
                pass
        else:
            # Headless mode
            await self.engine.run_loop()
            
    async def _run_ui(self):
        """Run Textual dashboard"""
        try:
            await self.dashboard.run_async()
        except Exception as e:
            self.logger.error(f"UI error: {e}")
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        if self.logger:
            self.logger.info("\n[SHUTDOWN] Stopping Kimmy Scalper...")
        self.running = False
        if self.engine:
            self.engine.stop()
        if self.dashboard and hasattr(self.dashboard, 'exit'):
            self.dashboard.exit()
            
    def stop(self):
        """Stop the bot"""
        self.running = False
        if self.engine:
            self.engine.stop()

def main():
    parser = argparse.ArgumentParser(description='Kimmy Scalper - Elite Crypto Trading Bot')
    parser.add_argument('--config', '-c', type=str, 
                       default='/root/.openclaw/workspace/KIMMY_SCALPER/config/config.yaml',
                       help='Path to config file')
    parser.add_argument('--paper', '-p', action='store_true', default=True,
                       help='Run in paper trading mode (default)')
    parser.add_argument('--live', '-l', action='store_true',
                       help='⚠️  Run in LIVE trading mode')
    parser.add_argument('--headless', action='store_true',
                       help='Run without UI')
    
    args = parser.parse_args()
    
    # Safety check
    if args.live:
        print("\n" + "="*60)
        print("⚠️  LIVE TRADING MODE")
        print("="*60)
        print("You are about to trade with REAL MONEY.")
        print("Make sure you have tested extensively in paper mode.")
        confirm = input("\nType 'LIVE' to confirm: ")
        if confirm != "LIVE":
            print("Aborted.")
            return
        args.paper = False
    else:
        print("\n" + "="*60)
        print("📊 PAPER TRADING MODE")
        print("="*60)
        print("Simulated trading with $1000 USDT")
        print("="*60 + "\n")
        
    # Create and run bot
    bot = KimmyBot(args.config, paper=args.paper)
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n[EXIT] Kimmy Scalper stopped")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
if __name__ == "__main__":
    main()
