"""
Kimmy Textual Dashboard
Professional terminal UI for live trading
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import (
    Header, Footer, DataTable, Static, Log, ProgressBar,
    Rule, Label, Sparkline, Input, Button
)
from textual.reactive import reactive
from textual.timer import Timer
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.sparkline import Sparkline

class PnLChart(Static):
    """Real-time P&L sparkline chart"""
    
    pnl_history = reactive([0.0] * 100)
    
    def update_chart(self, pnl_data: List[float]):
        self.pnl_history = pnl_data[-100:] if len(pnl_data) > 100 else pnl_data + [0.0] * (100 - len(pnl_data))
        self.refresh()
        
    def render(self):
        if not self.pnl_history or all(x == 0 for x in self.pnl_history):
            return Panel("[dim]Waiting for trades...[/]", title="P/L History", border_style="blue")
            
        color = "green" if self.pnl_history[-1] >= 0 else "red"
        chart = Sparkline(self.pnl_history)
        
        return Panel(
            str(chart),
            title=f"[bold]P/L History[/] ([{color}]{self.pnl_history[-1]:+.2%}[/])",
            border_style=color
        )

class OrderbookDisplay(Static):
    """Live orderbook visualization"""
    
    bids = reactive([])
    asks = reactive([])
    spread = reactive(0.0)
    
    def update_book(self, bids: List[tuple], asks: List[tuple]):
        self.bids = sorted(bids, key=lambda x: x[0], reverse=True)[:10]
        self.asks = sorted(asks, key=lambda x: x[0])[:10]
        if self.bids and self.asks:
            self.spread = (self.asks[0][0] - self.bids[0][0]) / self.bids[0][0] * 100
        self.refresh()
        
    def render(self):
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Vol", justify="right", style="cyan", width=8)
        table.add_column("Price", justify="right", style="red", width=12)
        table.add_column("Spread", justify="center", style="white", width=10)
        table.add_column("Price", justify="left", style="green", width=12)
        table.add_column("Vol", justify="left", style="cyan", width=8)
        
        # Header
        rows = []
        
        # Asks (descending)
        for price, vol in reversed(self.asks[-5:]):
            rows.append(("", "", "", f"{price:,.2f}", f"{vol:,.4f}"))
            
        # Spread row
        rows.append(("", "", f"[yellow]{self.spread:.3f}%[/]", "", ""))
        
        # Bids (descending)
        for price, vol in self.bids[:5]:
            rows.append((f"{vol:,.4f}", f"{price:,.2f}", "", "", ""))
            
        for row in rows:
            table.add_row(*row)
            
        return Panel(table, title="[bold]Orderbook[/]", border_style="blue")

class TradeTable(DataTable):
    """Recent trades display"""
    
    def __init__(self):
        super().__init__()
        self.add_columns("Time", "Pair", "Side", "Entry", "Exit", "P/L", "Reason")
        
    def add_trade(self, trade: dict):
        color = "green" if trade.get('pnl', 0) >= 0 else "red"
        self.add_row(
            trade.get('time', '--'),
            trade.get('pair', '--'),
            f"[{'green' if trade.get('side') == 'buy' else 'red'}]{trade.get('side', '--').upper()}[/]",
            f"{trade.get('entry', 0):,.2f}",
            f"{trade.get('exit', 0):,.2f}",
            f"[{color}]{trade.get('pnl', 0):+.2%}[/]",
            trade.get('reason', '--')
        )
        if self.row_count > 20:
            self.remove_row(self.row_count - 1)

class StatsPanel(Static):
    """Key statistics display"""
    
    balance = reactive(1000.0)
    total_pnl = reactive(0.0)
    win_rate = reactive(0.0)
    sharpe = reactive(0.0)
    drawdown = reactive(0.0)
    open_positions = reactive(0)
    daily_trades = reactive(0)
    
    def render(self):
        pnl_color = "green" if self.total_pnl >= 0 else "red"
        
        grid = Table.grid(padding=1)
        grid.add_column(style="bold", width=15)
        grid.add_column(style="cyan", width=15)
        grid.add_column(style="bold", width=15)
        grid.add_column(style="cyan", width=15)
        
        grid.add_row(
            "Balance:", f"${self.balance:,.2f}",
            "Total P/L:", f"[{pnl_color}]{self.total_pnl:+.2%}[/]"
        )
        grid.add_row(
            "Win Rate:", f"{self.win_rate:.1%}",
            "Sharpe:", f"{self.sharpe:.2f}"
        )
        grid.add_row(
            "Drawdown:", f"{self.drawdown:.2%}",
            "Open Pos:", str(self.open_positions)
        )
        grid.add_row(
            "Daily Trades:", str(self.daily_trades),
            "Status:", "[green]LIVE[/]" if self.open_positions > 0 else "[yellow]SCANNING[/]"
        )
        
        return Panel(grid, title="[bold]Statistics[/]", border_style="green")

class SignalPanel(Static):
    """Current strategy signals"""
    
    signal = reactive(None)
    confidence = reactive(0.0)
    imbalance = reactive(0.5)
    momentum = reactive(0.0)
    rsi = reactive(50.0)
    
    def render(self):
        if not self.signal:
            return Panel("[dim]No active signal[/]", title="Signals", border_style="dim")
            
        arrow = "▲" if self.signal == 'buy' else "▼"
        color = "green" if self.signal == 'buy' else "red"
        
        text = Text()
        text.append(f"Signal: ", style="bold")
        text.append(f"{arrow} {self.signal.upper()}", style=f"{color} bold")
        text.append(f"\nConfidence: {self.confidence:.1%}\n")
        text.append(f"Orderbook Imbalance: {self.imbalance:.1%}\n")
        text.append(f"Momentum: {self.momentum:+.2%}\n")
        text.append(f"RSI: {self.rsi:.1f}")
        
        return Panel(text, title="[bold]Strategy Signals[/]", border_style=color)

class KimmyDashboard(App):
    """Main Textual Application"""
    
    CSS = """
    Screen { align: center middle; }
    
    .header { dock: top; }
    .footer { dock: bottom; }
    
    #main-grid {
        grid-size: 3 3;
        grid-columns: 1fr 2fr 1fr;
        grid-rows: auto 1fr auto;
        height: 100%;
        margin: 1;
    }
    
    #stats { row-span: 1; column-span: 3; }
    #orderbook { row-span: 1; }
    #pnl-chart { row-span: 1; }
    #trades { row-span: 2; }
    #signals { row-span: 1; }
    #log { row-span: 1; height: 100%; }
    """
    
    TITLE = "🚀 Kimmy Scalper v2.0"
    SUB_TITLE = "Ultra-Low Latency Crypto Trading"
    
    def __init__(self, trading_engine=None):
        super().__init__()
        self.engine = trading_engine
        self.update_timer: Optional[Timer] = None
        self.pnl_data = []
        
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Grid(id="main-grid"):
            # Row 1: Stats
            yield StatsPanel(id="stats")
            
            # Row 2-3: Main content
            yield OrderbookDisplay(id="orderbook")
            yield PnLChart(id="pnl-chart")
            yield TradeTable(id="trades")
            yield SignalPanel(id="signals")
            yield Log(id="log", max_lines=100)
            
        yield Footer()
        
    def on_mount(self):
        """Start update loop"""
        self.update_timer = self.set_interval(2.0, self.refresh_data)
        self.query_one(Log).write("[green]Kimmy Scalper initialized[/]")
        self.query_one(Log).write("[yellow]Connecting to exchange...[/]")
        
    def refresh_data(self):
        """Update all panels with fresh data"""
        if not self.engine:
            return
            
        try:
            # Get data from engine
            stats = self.engine.get_stats()
            book = self.engine.get_orderbook()
            signal = self.engine.get_current_signal()
            trades = self.engine.get_recent_trades()
            
            # Update stats panel
            stats_panel = self.query_one(StatsPanel)
            stats_panel.balance = stats.get('balance', 1000)
            stats_panel.total_pnl = stats.get('total_pnl', 0)
            stats_panel.win_rate = stats.get('win_rate', 0)
            stats_panel.sharpe = stats.get('sharpe', 0)
            stats_panel.drawdown = stats.get('drawdown', 0)
            stats_panel.open_positions = stats.get('open_positions', 0)
            stats_panel.daily_trades = stats.get('daily_trades', 0)
            
            # Update orderbook
            book_panel = self.query_one(OrderbookDisplay)
            book_panel.update_book(book.get('bids', []), book.get('asks', []))
            
            # Update PNL chart
            self.pnl_data.append(stats.get('total_pnl', 0))
            pnl_panel = self.query_one(PnLChart)
            pnl_panel.update_chart(self.pnl_data)
            
            # Update signals
            signal_panel = self.query_one(SignalPanel)
            if signal:
                signal_panel.signal = signal.get('side')
                signal_panel.confidence = signal.get('confidence', 0)
                signal_panel.imbalance = signal.get('imbalance', 0.5)
                signal_panel.momentum = signal.get('momentum', 0)
                signal_panel.rsi = signal.get('rsi', 50)
                
            # Add new trades
            trades_table = self.query_one(TradeTable)
            for trade in trades:
                trades_table.add_trade(trade)
                
            # Log heartbeat
            log = self.query_one(Log)
            if stats.get('last_trade_time'):
                log.write(f"[dim]Heartbeat: {datetime.now().strftime('%H:%M:%S')} | "
                         f"Price: {book.get('mid', 0):,.2f} | "
                         f"Positions: {stats['open_positions']}[/]")
                         
        except Exception as e:
            log = self.query_one(Log)
            log.write(f"[red]Error: {str(e)}[/]")
            
    def action_quit(self):
        """Clean shutdown"""
        if self.engine:
            self.engine.stop()
        self.exit()

# Entry point
if __name__ == "__main__":
    # For testing UI without engine
    app = KimmyDashboard()
    app.run()
