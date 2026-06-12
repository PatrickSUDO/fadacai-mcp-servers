import sys
import json

# This will simulate calling the tool
ticker = "SNOW"
period = "3mo"

# Import yfinance
import yfinance as yf
from talib import RSI, MACD, ATR, BBANDS, SMA

try:
    # Download data
    df = yf.download(ticker, period=period, progress=False)
    
    # Calculate technical indicators
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    
    rsi = RSI(close, timeperiod=14)[-1]
    macd, signal, histogram = MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    atr = ATR(high, low, close, timeperiod=14)[-1]
    
    print(json.dumps({
        "ticker": ticker,
        "period": period,
        "rsi_14": float(rsi) if not (rsi != rsi) else None,
        "macd_line": float(macd[-1]) if len(macd) > 0 and macd[-1] == macd[-1] else None,
        "macd_signal": float(signal[-1]) if len(signal) > 0 and signal[-1] == signal[-1] else None,
        "macd_histogram": float(histogram[-1]) if len(histogram) > 0 and histogram[-1] == histogram[-1] else None,
        "atr": float(atr),
        "current_price": float(df['Close'].iloc[-1]),
        "52_week_high": float(df['High'].max()),
        "52_week_low": float(df['Low'].min()),
    }, indent=2))
    
except Exception as e:
    print(json.dumps({"error": str(e)}, indent=2))

