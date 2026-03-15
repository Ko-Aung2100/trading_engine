import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

def run_backtest(csv_path="data/spy_2000-2020.csv"):
    """Runs a backtest using local CSV data."""
    
    # 1. Load Local Historical Data
    try:
        df = pd.read_csv(csv_path, parse_dates=['Date'], index_col='Date')
    except FileNotFoundError:
        fig = go.Figure().add_annotation(text=f"File not found: {csv_path}", showarrow=False, font=dict(size=20))
        return fig, 0.0, 0
    
    # 2. Calculate Indicators
    df.ta.sma(length=50, append=True)  # Using standard 50/200 for SPY daily data
    df.ta.sma(length=200, append=True)
    df.dropna(inplace=True) 
    
    trades = []
    buy_signals = []
    sell_signals = []
    position = None
    buy_price = 0
    
    # 3. Simulate Bar-by-Bar
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
                
    # 4. Calculate Stats
    wins = [t for t in trades if t > 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    
    # 5. Build Chart
    fig = go.Figure()
    
    # --- UPDATED: Candlestick trace instead of Scatter ---
    fig.add_trace(go.Candlestick(
        x=df.index, 
        open=df['Open'], 
        high=df['High'], 
        low=df['Low'], 
        close=df['Close'], 
        name='Price'
    ))
    
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50', line=dict(color='cyan')))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='SMA 200', line=dict(color='orange')))
    
    if buy_signals:
        bx, by = zip(*buy_signals)
        fig.add_trace(go.Scatter(x=bx, y=by, mode='markers', name='Buy', marker=dict(symbol='triangle-up', color='green', size=12)))
    if sell_signals:
        sx, sy = zip(*sell_signals)
        fig.add_trace(go.Scatter(x=sx, y=sy, mode='markers', name='Sell', marker=dict(symbol='triangle-down', color='red', size=12)))
        
    # --- UPDATED: Added xaxis_rangeslider_visible=False to match main.py ---
    fig.update_layout(
        template='plotly_dark', 
        margin=dict(l=10, r=10, t=10, b=10), 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False
    )
    
    return fig, win_rate, len(trades)