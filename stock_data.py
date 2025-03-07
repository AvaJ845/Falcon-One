#stock_data.py
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

@st.cache_data(ttl=600)  # Cache data for 10 minutes
def fetch_stock_data(ticker, period="1d", interval="1m"):
    """
    Fetch stock data for the given ticker
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period to fetch data for (default: 1 day)
    interval (str): Data interval (default: 1 minute)
    
    Returns:
    pandas.DataFrame: DataFrame containing stock price data
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        return df
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return pd.DataFrame()


def get_stock_info(ticker):
    """
    Get comprehensive stock information
    
    Parameters:
    ticker (str): Stock ticker symbol
    
    Returns:
    dict: Dictionary containing stock information
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract key metrics
        metrics = {
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'beta': info.get('beta', 0),
            'avg_volume': info.get('averageVolume', 0),
            '52wk_high': info.get('fiftyTwoWeekHigh', 0),
            '52wk_low': info.get('fiftyTwoWeekLow', 0),
            'analyst_target': info.get('targetMeanPrice', 0)
        }
        
        return metrics
    except Exception as e:
        st.error(f"Error fetching info for {ticker}: {str(e)}")
        return {}


def calculate_historical_volatility(ticker, days=20):
    """
    Calculate historical volatility for a given stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    days (int): Number of days to calculate volatility for
    
    Returns:
    float: Annualized volatility as a percentage
    """
    try:
        # Get data for a bit longer than the requested period to ensure we have enough
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days*2)  
        
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        # Calculate daily returns
        df['daily_return'] = df['Close'].pct_change()
        
        # Calculate volatility (standard deviation of returns)
        daily_volatility = df['daily_return'].tail(days).std()
        
        # Annualize volatility (assuming 252 trading days in a year)
        annualized_volatility = daily_volatility * (252 ** 0.5)
        
        return annualized_volatility * 100  # Convert to percentage
    except Exception as e:
        st.error(f"Error calculating volatility for {ticker}: {str(e)}")
        return 0.0

def get_intraday_volatility(ticker, days=5):
    """
    Calculate average intraday volatility for a stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    days (int): Number of days to consider
    
    Returns:
    float: Average intraday volatility as a percentage
    """
    try:
        # Fetch intraday data
        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{days}d", interval="5m")
        
        # Group by date
        df['Date'] = df.index.date
        daily_groups = df.groupby('Date')
        
        # Calculate daily intraday volatility (high-low range as percentage of open)
        daily_volatility = []
        
        for date, group in daily_groups:
            daily_high = group['High'].max()
            daily_low = group['Low'].min()
            daily_open = group['Open'].iloc[0]
            
            volatility = (daily_high - daily_low) / daily_open * 100
            daily_volatility.append(volatility)
        
        # Return average intraday volatility
        return np.mean(daily_volatility)
    
    except Exception as e:
        st.warning(f"Error calculating intraday volatility for {ticker}: {str(e)}")
        return 0.0

def get_best_day_trading_stocks():
    """
    Get a list of stocks that are good for day trading
    based on liquidity, volatility, and volume
    
    Returns:
    list: List of ticker symbols
    """
    # For demo purposes, return a curated list
    # In a production app, this would use real-time screener data
    day_trading_candidates = [
        "AAPL", "TSLA", "NVDA", "AMD", "AMZN", "MSFT", "META", "NFLX", 
        "GOOG", "SPY", "QQQ", "COIN", "ROKU", "SHOP", "PYPL", "SQ", 
        "DIS", "BA", "PLTR", "NIO", "SNAP", "ABNB", "UBER", "RBLX"
    ]
    
    return day_trading_candidates

def get_premarket_movers():
    """
    Get stocks that are moving significantly in pre-market trading
    
    Returns:
    DataFrame: DataFrame with pre-market movers
    """
    # In a production app, this would use real pre-market data
    # For demo, we'll simulate this with random data
    
    tickers = get_best_day_trading_stocks()
    
    premarket_data = []
    for ticker in tickers[:10]:  # Use subset for demo
        try:
            stock_info = get_stock_info(ticker)
            last_close = fetch_stock_data(ticker, period="2d")['Close'].iloc[-2]
            
            # Simulate pre-market price change with random data
            premarket_change = np.random.normal(0, 2)  # Random change with normal distribution
            premarket_price = last_close * (1 + premarket_change/100)
            
            premarket_data.append({
                'Symbol': ticker,
                'Company': stock_info.get('name', ticker),
                'Last Close': last_close,
                'Pre-market Price': premarket_price,
                'Pre-market Change %': premarket_change,
                'Volume': int(np.random.randint(10000, 1000000))
            })
        except:
            pass
    
    # Convert to DataFrame and sort by absolute change
    premarket_df = pd.DataFrame(premarket_data)
    if not premarket_df.empty:
        premarket_df['Abs Change'] = premarket_df['Pre-market Change %'].abs()
        premarket_df = premarket_df.sort_values('Abs Change', ascending=False).drop('Abs Change', axis=1)
    
    return premarket_df

def get_day_trading_metrics(ticker):
    """
    Calculate key day trading metrics for a stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    
    Returns:
    dict: Dictionary of day trading metrics
    """
    try:
        # Get recent data
        daily_data = fetch_stock_data(ticker, period="10d", interval="1d")
        intraday_data = fetch_stock_data(ticker, period="5d", interval="5m")
        
        # Calculate average daily range
        daily_data['daily_range'] = daily_data['High'] - daily_data['Low']
        avg_daily_range = daily_data['daily_range'].mean()
        
        # Calculate average volume
        avg_volume = daily_data['Volume'].mean()
        
        # Calculate intraday volatility
        intraday_vol = get_intraday_volatility(ticker)
        
        # Get current price
        current_price = daily_data['Close'].iloc[-1]
        
        # Suggested stop loss (2x average intraday volatility)
        stop_loss = current_price * (1 - intraday_vol/100 * 2)
        
        # Suggested profit target (1.5x stop loss distance)
        profit_distance = current_price - stop_loss
        profit_target = current_price + (profit_distance * 1.5)
        
        # Calculate typical price moves by time of day
        intraday_data['hour'] = intraday_data.index.hour
        
        hourly_moves = {}
        for hour, group in intraday_data.groupby('hour'):
            if len(group) > 5:  # Make sure we have enough data
                hourly_moves[hour] = (group['High'].max() - group['Low'].min()) / group['Open'].iloc[0] * 100
        
        # Determine best entry time (hour with typically largest moves)
        best_entry = max(hourly_moves.items(), key=lambda x: x[1])[0] if hourly_moves else 9
        best_entry_time = f"{best_entry}:30 AM" if best_entry < 12 else f"{best_entry-12}:30 PM"
        
        # Calculate liquidity score (1-10 scale based on volume and spread)
        volume_score = min(10, avg_volume / 1000000)
        liquidity_score = round(volume_score)
        
        return {
            'avg_daily_range': avg_daily_range,
            'intraday_volatility': intraday_vol,
            'avg_volume': avg_volume,
            'stop_loss': stop_loss,
            'profit_target': profit_target,
            'best_entry_time': best_entry_time,
            'liquidity_score': liquidity_score
        }
    
    except Exception as e:
        st.warning(f"Error calculating day trading metrics for {ticker}: {str(e)}")
        return {
            'avg_daily_range': 0.0,
            'intraday_volatility': 0.0,
            'avg_volume': 0,
            'stop_loss': 0.0,
            'profit_target': 0.0,
            'best_entry_time': "9:30 AM",
            'liquidity_score': 5
        }