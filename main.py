import os
import asyncio
import requests
import pandas as pd
import pandas_ta as ta
import flet as ft
import flet_fastapi
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
import plotly.graph_objects as go
from flet.plotly_chart import PlotlyChart

from backtester import run_backtest
from core.state_manager import state
from strategies.strategy_factory import StrategyFactory

# --- 0. Network Fix: Clear "Ghost" Proxies left by VPNs ---
for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(k, None)

# --- 1. Background Market Scanner (Direct API Bypass) ---
async def market_scanner():
    print("Market Scanner Started: Monitoring BTC/USDT directly via API...")
    last_signal = None 
    
    while True:
        try:
            # 1. Fetch data directly in a background thread to prevent Flet UI freezing
            def fetch_data():
                # api4.binance.com is the official fallback URL to bypass ISP blocks
                url = "https://api4.binance.com/api/v3/klines"
                params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 60}
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()

            # Execute the request
            data = await asyncio.to_thread(fetch_data)
            
            # 2. Convert the raw Binance JSON array directly to our DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', '_', '_', '_', '_', '_', '_'])
            df = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            if not df.empty and len(df) > 21:
                # Calculate MAs for the chart and logic
                df.ta.sma(length=9, append=True)
                df.ta.sma(length=21, append=True)
                
                # Update the State Manager so the UI can draw the live chart
                state.update_live_data(df)
                
                last_row = df.iloc[-2] # Last closed candle
                current_price = last_row['Close']
                sma_fast = last_row['SMA_9']
                sma_slow = last_row['SMA_21']

                # 3. Check for Crossover
                action = None
                if sma_fast > sma_slow and last_signal != "BUY":
                    action = "BUY"
                elif sma_fast < sma_slow and last_signal != "SELL":
                    action = "SELL"

                # 4. Trigger Execution
                if action:
                    last_signal = action
                    payload = {"strategy_id": "golden_cross", "action": action, "symbol": "BTC/USDT", "price": current_price}
                    strategy_instance = StrategyFactory.get_strategy("golden_cross")
                    await strategy_instance.execute(payload, state)

        except Exception as e:
            # Added error types so we can see exactly what fails if it happens again
            print(f"Scanner Error: [{type(e).__name__}] {e}")
        
        await asyncio.sleep(60) # Wait 1 minute for the next candle

@asynccontextmanager
async def lifespan(app: FastAPI):
    scanner_task = asyncio.create_task(market_scanner())
    yield
    scanner_task.cancel()

app = FastAPI(title="Algorithmic Trading Engine", lifespan=lifespan)

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    payload = await request.json()
    strategy_instance = StrategyFactory.get_strategy(payload.get("strategy_id"))
    return await strategy_instance.execute(payload, state)

# --- 2. Flet Frontend Dashboard ---
async def flet_ui(page: ft.Page):
    page.title = "Trading Engine Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # --- LIVE TAB COMPONENTS ---
    live_chart_container = ft.Container(expand=True)
    trade_list = ft.ListView(height=200, spacing=10) 
    
    async def update_live_ui():
        # 1. Update the Live Chart
        if not state.live_df.empty:
            df = state.live_df
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_9'], name='SMA 9', line=dict(color='cyan', width=1)))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_21'], name='SMA 21', line=dict(color='orange', width=1)))
            fig.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            live_chart_container.content = PlotlyChart(fig, expand=True)

        # 2. Update the Trade Logs
        trade_list.controls.clear()
        for trade in reversed(state.trade_history):
            color = ft.colors.GREEN_700 if trade["action"] == "BUY" else ft.colors.RED_700
            card = ft.Card(content=ft.Container(padding=10, content=ft.Row([
                ft.Text(f"{trade['symbol']} {trade['action']} @ ${trade.get('price', '')}", color=color, weight="bold"),
                ft.Text(trade['timestamp'], size=12)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)))
            trade_list.controls.append(card)
            
        await page.update_async()

    state.register_callback(update_live_ui)

    # --- BACKTEST TAB COMPONENTS ---
    bt_chart_container = ft.Container(expand=True)
    stats_text = ft.Text("Run a backtest using local CSV data.", size=16, weight="bold")
    
    # New: Dropdown to control the zoom level
    zoom_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("100", "100 Candles (Zoomed In)"),
            ft.dropdown.Option("300", "300 Candles"),
            ft.dropdown.Option("1000", "1000 Candles"),
            ft.dropdown.Option("0", "All Time (Fully Zoomed Out)")
        ],
        value="300", # Default to 300 for a clear candlestick view
        width=250,
        label="Chart Zoom Level"
    )
    
    async def btn_run_backtest(e):
        stats_text.value = "Running backtest... please wait."
        bt_chart_container.content = ft.ProgressRing()
        await page.update_async()
        
        # Pass the dropdown value into the backtester!
        lookback = int(zoom_dropdown.value)
        fig, win_rate, total_trades = run_backtest(csv_path="data/spy_2000-2020.csv", chart_lookback=lookback)
        
        stats_text.value = f"Results: {total_trades} Trades | Win Rate: {win_rate:.2f}%"
        bt_chart_container.content = PlotlyChart(fig, expand=True)
        await page.update_async()

    # --- MAIN LAYOUT ---
    tabs = ft.Tabs(
        selected_index=0, expand=True,
        tabs=[
            ft.Tab(text="Live Market (BTC/USDT)", icon=ft.icons.BOLT, content=ft.Column([
                ft.Text("Live Chart (Updates every 60s)", weight="bold", color=ft.colors.BLUE_200),
                live_chart_container, 
                ft.Divider(), 
                ft.Text("Execution Logs", weight="bold"),
                trade_list
            ])),
            ft.Tab(text="Backtest Analyzer (SPY)", icon=ft.icons.QUERY_STATS, content=ft.Column([
                ft.Row([
                    ft.ElevatedButton("Run SPY Backtest", on_click=btn_run_backtest, icon=ft.icons.PLAY_ARROW),
                    zoom_dropdown  # Add the dropdown to the row!
                ]),
                stats_text, ft.Divider(), bt_chart_container
            ]))
        ]
    )
    await page.add_async(ft.Row([ft.Icon(ft.icons.SHOW_CHART, size=30, color=ft.colors.BLUE_400), ft.Text("Algorithmic Engine", size=24, weight="bold")]), tabs)

app.mount("/", flet_fastapi.app(flet_ui))