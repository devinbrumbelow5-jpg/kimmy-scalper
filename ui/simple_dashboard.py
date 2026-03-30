"""
Kimmy Simple Dashboard - Rich-based Terminal UI
Fallback dashboard that works without Textual
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from rich.text import Text
from rich.align import Align

console = Console()

class SimpleDashboard:
    """Simple Rich-based dashboard that runs in any terminal"""
    
    def __init__(self, trading_engine=None):
        self.engine = trading_engine
        self.running = False
        self.layout = None
        
    def exit(self):
        """Exit the dashboard"""
        self.running = False
        
    def create_header(self) -> Panel:
        """Create header panel"""
        title = Text("🚀 KIMMY SCALPER v2.0", style="bold cyan")
        subtitle = Text("Elite Ultra-Low Latency Crypto Trading", style="dim")
        
        header_text = Text.assemble(
            title, "\n", subtitle
        )
        return Panel(header_text, style="cyan", box=box.DOUBLE)
        
    def create_stats(self, stats: dict) -> Panel:
        """Create statistics panel"""
        if not stats:
            return Panel("[dim]Loading...[/]")
            
        balance = stats.get('balance', 1000)
        total_pnl = stats.get('total_pnl', 0)
        win_rate = stats.get('win_rate', 0)
        open_pos = stats.get('open_positions', 0)
        total_trades = stats.get('total_trades', 0)
        
        pnl_color = "green" if total_pnl >= 0 else "red"
        
        table = Table(show_header=False, box=None)
        table.add_column(style="cyan")
        table.add_column(style="white")
        table.add_column(style="cyan")
        table.add_column(style="white")
        
        table.add_row(
            "Balance:", f"${balance:,.2f}",
            "Total P/L:", f"[{pnl_color}]{total_pnl:+.2%}[/{pnl_color}]"
        )
        table.add_row(
            "Win Rate:", f"{win_rate:.1%}",
            "Open Pos:", str(open_pos)
        )
        table.add_row(
            "Trades:", str(total_trades),
            "Status:", "[green]ACTIVE[/]" if open_pos > 0 else "[yellow]SCANNING[/]"
        )
        
        return Panel(table, title="[bold]Statistics[/]", border_style="green")
        
    def create_orderbook(self, book: dict) -> Panel:
        """Create orderbook panel"""
        bids = book.get('bids', [])
        asks = book.get('asks', [])
        
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Bid Vol", style="green", justify="right")
        table.add_column("Bid", style="green", justify="right")
        table.add_column("Spread", style="yellow", justify="center")
        table.add_column("Ask", style="red", justify="left")
        table.add_column("Ask Vol", style="red", justify="left")
        
        # Show top 5 levels
        for i in range(5):
            bid_vol = f"{bids[i][1]:.4f}" if i < len(bids) else ""
            bid_price = f"{bids[i][0]:,.2f}" if i < len(bids) else ""
            ask_price = f"{asks[i][0]:,.2f}" if i < len(asks) else ""
            ask_vol = f"{asks[i][1]:.4f}" if i < len(asks) else ""
            
            spread = ""
            if i == 0 and bids and asks:
                spread_pct = (asks[0][0] - bids[0][0]) / bids[0][0] * 100
                spread = f"{spread_pct:.3f}%"
                
            table.add_row(bid_vol, bid_price, spread, ask_price, ask_vol)
            
        return Panel(table, title="[bold]Orderbook[/]", border_style="blue")
        
    def create_trades(self, trades: List[dict]) -> Panel:
        """Create trade history panel"""
        if not trades:
            return Panel("[dim]No trades yet...[/]", title="[bold]Trade History[/]")
            
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Time", style="dim")
        table.add_column("Side", style="bold")
        table.add_column("Entry", justify="right")
        table.add_column("Exit", justify="right")
        table.add_column("P/L", justify="right")
        table.add_column("Reason", style="dim")
        
        for t in trades[:10]:  # Show last 10
            side_color = "green" if t.get('side') == 'long' else "red"
            pnl = t.get('pnl', 0)
            pnl_color = "green" if pnl >= 0 else "red"
            
            table.add_row(
                t.get('time', '--'),
                f"[{side_color}]{t.get('side', '--').upper()}[/{side_color}]",
                f"{t.get('entry', 0):,.2f}",
                f"{t.get('exit', 0):,.2f}",
                f"[{pnl_color}]{pnl:+.2%}[/{pnl_color}]",
                t.get('reason', '--')
            )
            
        return Panel(table, title="[bold]Trade History[/]", border_style="magenta")
        
    def create_footer(self, signal: dict) -> Panel:
        """Create footer with current signal"""
        if not signal:
            return Panel("[dim]No active signal[/]", title="[bold]Strategy Signal[/]")
            
        side = signal.get('side')
        confidence = signal.get('confidence', 0)
        
        if side:
            color = "green" if side == 'buy' else "red"
            arrow = "▲" if side == 'buy' else "▼"
            
            text = Text.assemble(
                (f"{arrow} {side.upper()} ", f"bold {color}"),
                (f"Confidence: {confidence:.1%}", "white")
            )
            return Panel(Align.center(text), title="[bold]Signal[/]", border_style=color)
            
        return Panel("[dim]Scanning...[/]", title="[bold]Signal[/]")
        
    def update(self) -> Layout:
        """Update the entire dashboard"""
        if self.layout is None:
            return Layout()
            
        if self.engine:
            stats = self.engine.get_stats()
            book = self.engine.get_orderbook()
            signal = self.engine.get_current_signal()
            trades = self.engine.get_recent_trades()
        else:
            stats = {}
            book = {'bids': [], 'asks': []}
            signal = None
            trades = []
            
        self.layout["header"].update(self.create_header())
        self.layout["stats"].update(self.create_stats(stats))
        self.layout["orderbook"].update(self.create_orderbook(book))
        self.layout["trades"].update(self.create_trades(trades))
        self.layout["footer"].update(self.create_footer(signal))
        
        return self.layout
        
    async def run(self):
        """Run the dashboard with live updates"""
        self.running = True
        
        # Initialize layout here
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=8),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5)
        )
        self.layout["main"].split_row(
            Layout(name="orderbook", ratio=1),
            Layout(name="trades", ratio=2)
        )
        
        with Live(console=console, screen=False, refresh_per_second=2) as live:
            while self.running:
                live.update(self.update())
                await asyncio.sleep(0.5)  # 2Hz refresh

# For testing without engine
if __name__ == "__main__":
    dashboard = SimpleDashboard()
    asyncio.run(dashboard.run())
