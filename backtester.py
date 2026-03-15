import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

def run_backtest(csv_path="data/spy_2000-2020.csv", chart_lookback=200):
    """Runs a backtest and zooms the chart to the most recent N candles."""
    
    # 1. Load Local Historical Data
    try:
        df = pd.read_csv(csv_path, parse_dates=['Date'], index_col='Date')
    except FileNotFoundError:
        fig = go.Figure().add_annotation(text=f"File not found: {csv_path}", showarrow=False, font=dict(size=20))
        return fig, 0.0, 0
    
    # 2. Calculate Indicators
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)
    df.dropna(inplace=True) 
    
    trades = []
    buy_signals = []
    sell_signals = []
    position = None
    buy_price = 0
    
    # 3. Simulate Bar-by-Bar (Calculates over the ENTIRE dataset for accurate stats)
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        
        # Buy Condition
        if prev['SMA_50'] <= prev['SMA_200'] and curr['SMA_50'] > curr['SMA_200']:
            if position != "BUY":
                position = "BUY"
                buy_price = curr['Close']
                buy_signals.append((df.index[i], curr['Close']))
                
        # Sell Condition
        elif prev['SMA_50'] >= prev['SMA_200'] and curr['SMA_50'] < curr['SMA_200']:
            if position == "BUY":
                position = None
                profit = curr['Close'] - buy_price
                trades.append(profit)
                sell_signals.append((df.index[i], curr['Close']))
                
    # 4. SLICE DATA FOR CHARTING (The "Zoom" Feature)
    if chart_lookback > 0 and chart_lookback < len(df):
        plot_df = df.tail(chart_lookback)
    else:
        plot_df = df # 0 means show all data
        
    # Only plot the buy/sell arrows that actually happened within our zoomed window
    plot_buys = [(x, y) for x, y in buy_signals if x >= plot_df.index[0]]
    plot_sells = [(x, y) for x, y in sell_signals if x >= plot_df.index[0]]
                
    # 5. Calculate Stats
    wins = [t for t in trades if t > 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    
    # 6. Build the Zoomed Chart
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'
    ))
    
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA_50'], name='SMA 50', line=dict(color='cyan')))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA_200'], name='SMA 200', line=dict(color='orange')))
    
    if plot_buys:
        bx, by = zip(*plot_buys)
        fig.add_trace(go.Scatter(x=bx, y=by, mode='markers', name='Buy', marker=dict(symbol='triangle-up', color='green', size=12)))
    if plot_sells:
        sx, sy = zip(*plot_sells)
        fig.add_trace(go.Scatter(x=sx, y=sy, mode='markers', name='Sell', marker=dict(symbol='triangle-down', color='red', size=12)))
        
    fig.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
    
    return fig, win_rate, len(trades)