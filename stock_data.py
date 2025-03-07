# stock_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import time

try:
    import yfinance as yf
except ImportError:
    st.error("yfinance package is not installed. Please run: pip install yfinance")

# Initialize session state
if 'use_mock_data' not in st.session_state:
    st.session_state.use_mock_data = False

def fetch_stock_data(ticker, period="1d", interval="1m", start=None, end=None, max_retries=5):
    """Fetch stock data with improved error handling"""
    
    # Check session state for mock data preference
    if st.session_state.get('use_mock_data', False):
        return generate_mock_data(ticker, period, interval)
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(
                period=period if not start else None,
                interval=interval,
                start=start,
                end=end,
                timeout=10
            )
            
            if not df.empty and len(df) >= 2:
                return df
            
            time.sleep(2)
        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to fetch {ticker} data, using mock data")
                return generate_mock_data(ticker, period, interval)
            time.sleep(2)
    
    return generate_mock_data(ticker, period, interval)

def generate_mock_data(ticker, period="1d", interval="1m"):
    """
    Generate mock stock data for demonstration purposes
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period to generate data for
    interval (str): Data interval
    
    Returns:
    pandas.DataFrame: DataFrame containing mock stock price data
    """
    # Determine number of data points based on period and interval
    periods_map = {"1d": 390, "5d": 5*390, "1mo": 21*390, "3mo": 63*390}
    intervals_map = {"1m": 1, "2m": 2, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "1d": 390}
    
    if period in periods_map and interval in intervals_map:
        n_points = periods_map[period] // intervals_map[interval]
    else:
        n_points = 100  # Default
    
    # Generate dates
    end_date = datetime.now()
    if interval == "1d":
        # For daily data
        dates = [end_date - timedelta(days=i) for i in range(n_points)]
    else:
        # For intraday data
        dates = [end_date - timedelta(minutes=i*intervals_map.get(interval, 5)) for i in range(n_points)]
    dates = sorted(dates)
    
    # Generate price data
    base_price = 100  # Default price
    if ticker == "AAPL": base_price = 180
    elif ticker == "MSFT": base_price = 320
    elif ticker == "GOOGL": base_price = 130
    elif ticker == "AMZN": base_price = 150
    elif ticker == "TSLA": base_price = 240
    elif ticker == "META": base_price = 490
    elif ticker == "NVDA": base_price = 850
    
    # Create mock price movement with some randomness based on ticker
    np.random.seed(hash(ticker) % 10000)  # Consistent randomness per ticker
    volatility = 0.01  # Base volatility 1%
    
    # Adjust volatility based on ticker (some stocks are more volatile)
    if ticker in ["TSLA", "NVDA", "COIN"]:
        volatility = 0.02  # Higher volatility stocks
    
    changes = np.random.normal(0, 1, n_points) * base_price * volatility
    prices = [base_price]
    for change in changes:
        prices.append(max(0.1, prices[-1] + change))
    prices = prices[1:]  # Remove the initial base price
    
    # Create OHLC data
    data = {
        'Open': prices,
        'Close': [p * (1 + np.random.normal(0, 0.002)) for p in prices],
        'High': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'Low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'Volume': [int(np.random.normal(1000000, 500000)) for _ in range(n_points)]
    }
    
    # Create DataFrame
    df = pd.DataFrame(data, index=dates)
    
    # Ensure data is properly sorted by date
    df = df.sort_index()
    
    return df

def fetch_stock_data(ticker, period="1d", interval="1m", start=None, end=None, max_retries=5, use_mock_data=False):
    """
    Fetch stock data for the given ticker with improved error handling
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period to fetch data for (default: 1 day)
    interval (str): Data interval (default: 1 minute)
    start (str): Start date in YYYY-MM-DD format (overrides period if provided)
    end (str): End date in YYYY-MM-DD format
    max_retries (int): Maximum number of retry attempts
    use_mock_data (bool): Force use of mock data even if API is working
    
    Returns:
    pandas.DataFrame: DataFrame containing stock price data
    """
    # If mock data is requested, generate it directly
    if use_mock_data:
        return generate_mock_data(ticker, period, interval)
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Add timeout parameter
            stock = yf.Ticker(ticker)
            
            if start and end:
                df = stock.history(start=start, end=end, interval=interval, timeout=10)
            else:
                df = stock.history(period=period, interval=interval, timeout=10)
            
            # Check if dataframe is empty or contains minimal data
            if df.empty or len(df) < 2:
                retry_count += 1
                if retry_count >= max_retries:
                    # Return mock data if all retries fail
                    st.warning(f"Insufficient data for {ticker} after {max_retries} attempts. Using mock data.")
                    return generate_mock_data(ticker, period, interval)
                time.sleep(2)  # Longer wait before retrying
                continue
                
            return df
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.warning(f"Error fetching data for {ticker} after {max_retries} attempts: {str(e)}. Using mock data.")
                return generate_mock_data(ticker, period, interval)
            time.sleep(2)  # Longer wait before retrying

def get_stock_info(ticker, max_retries=3):
    """
    Get comprehensive stock information
    
    Parameters:
    ticker (str): Stock ticker symbol
    max_retries (int): Maximum number of retry attempts
    
    Returns:
    dict: Dictionary containing stock information
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            stock = yf.Ticker(ticker)
            
            # Try to get info from ticker info attribute
            try:
                info = stock.info
            except Exception as e:
                # Try one more time with a delay
                time.sleep(1)
                try:
                    info = stock.info
                except Exception as e2:
                    st.warning(f"Could not fetch full info for {ticker}, using basic info instead.")
                    
                    # Create a minimal info dict if the detailed info isn't available
                    price_data = fetch_stock_data(ticker, period="1d")
                    
                    if not price_data.empty:
                        info = {
                            'longName': ticker,
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'marketCap': 0,
                            'trailingPE': 0,
                            'dividendYield': 0,
                            'beta': 0,
                            'averageVolume': price_data['Volume'].iloc[0] if 'Volume' in price_data.columns else 0,
                            'fiftyTwoWeekHigh': price_data['High'].max() if 'High' in price_data.columns else 0,
                            'fiftyTwoWeekLow': price_data['Low'].min() if 'Low' in price_data.columns else 0,
                            'targetMeanPrice': 0
                        }
                    else:
                        # If we can't even get price data, use mock data
                        mock_data = generate_mock_data(ticker, "1mo", "1d")
                        info = {
                            'longName': ticker,
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'marketCap': 0,
                            'trailingPE': 0,
                            'dividendYield': 0,
                            'beta': 0,
                            'averageVolume': mock_data['Volume'].iloc[0] if 'Volume' in mock_data.columns else 0,
                            'fiftyTwoWeekHigh': mock_data['High'].max() if 'High' in mock_data.columns else 0,
                            'fiftyTwoWeekLow': mock_data['Low'].min() if 'Low' in mock_data.columns else 0,
                            'targetMeanPrice': 0
                        }
            
            # Extract key metrics with safer access
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
            retry_count += 1
            if retry_count >= max_retries:
                # Return basic information with ticker name if there's an error
                st.warning(f"Error fetching info for {ticker}: {str(e)}. Using minimal info.")
                
                # Generate mock data for the stock
                mock_data = generate_mock_data(ticker, "1mo", "1d")
                current_price = mock_data['Close'].iloc[-1] if not mock_data.empty else 100
                
                # Return minimal stock information
                return {
                    'name': f"{ticker} Inc.",
                    'sector': 'Technology',
                    'industry': 'Software',
                    'market_cap': current_price * 1000000000,  # Simulate market cap
                    'pe_ratio': 20 + np.random.normal(0, 5),  # Realistic P/E ratio
                    'dividend_yield': max(0, np.random.normal(1.5, 1)),  # Realistic dividend yield
                    'beta': max(0, np.random.normal(1.1, 0.3)),  # Realistic beta
                    'avg_volume': int(np.random.normal(5000000, 2000000)),  # Realistic volume
                    '52wk_high': current_price * (1 + abs(np.random.normal(0, 0.15))),  # Realistic 52-week high
                    '52wk_low': current_price * (1 - abs(np.random.normal(0, 0.15))),  # Realistic 52-week low
                    'analyst_target': current_price * (1 + np.random.normal(0, 0.1))  # Realistic target price
                }
            time.sleep(1)  # Wait before retrying

def calculate_historical_volatility(ticker, days=20, max_retries=3):
    """
    Calculate historical volatility for a given stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    days (int): Number of days to calculate volatility for
    max_retries (int): Maximum number of retry attempts
    
    Returns:
    float: Annualized volatility as a percentage
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Get data for a bit longer than the requested period to ensure we have enough
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days*2)  
            
            # Fetch stock data
            df = fetch_stock_data(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
            
            # If we got enough data, proceed with calculation
            if len(df) >= days:
                # Calculate daily returns
                df['daily_return'] = df['Close'].pct_change()
                
                # Calculate volatility (standard deviation of returns)
                daily_volatility = df['daily_return'].tail(days).std()
                
                # Annualize volatility (assuming 252 trading days in a year)
                annualized_volatility = daily_volatility * (252 ** 0.5)
                
                return annualized_volatility * 100  # Convert to percentage
            else:
                # Not enough data, try with a longer period
                retry_count += 1
                if retry_count >= max_retries:
                    st.warning(f"Insufficient data to calculate volatility for {ticker}")
                    # Return a simulated volatility for demo purposes
                    if ticker in ["TSLA", "NVDA", "COIN", "GME", "AMC"]:
                        return np.random.uniform(40, 60)  # High volatility stocks
                    elif ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
                        return np.random.uniform(20, 35)  # Medium volatility stocks
                    else:
                        return np.random.uniform(10, 25)  # Lower volatility stocks
                time.sleep(1)
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.warning(f"Error calculating volatility for {ticker}: {str(e)}")
                # Return a simulated volatility for demo purposes
                if ticker in ["TSLA", "NVDA", "COIN", "GME", "AMC"]:
                    return np.random.uniform(40, 60)  # High volatility stocks
                elif ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
                    return np.random.uniform(20, 35)  # Medium volatility stocks
                else:
                    return np.random.uniform(10, 25)  # Lower volatility stocks
            time.sleep(1)


def get_intraday_volatility(ticker, days=5, max_retries=3):
    """
    Calculate average intraday volatility for a stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    days (int): Number of days to consider
    max_retries (int): Maximum number of retry attempts
    
    Returns:
    float: Average intraday volatility as a percentage
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Fetch intraday data
            df = fetch_stock_data(ticker, period=f"{days*2}d", interval="5m")
            
            # If we have enough data points, proceed
            if len(df) > days * 50:  # Expect ~78 5-min bars per day (6.5 hours)
                # Group by date
                df['Date'] = df.index.date
                daily_groups = df.groupby('Date')
                
                # Calculate daily intraday volatility (high-low range as percentage of open)
                daily_volatility = []
                
                for date, group in daily_groups:
                    if len(group) > 10:  # Ensure we have sufficient data points for this day
                        daily_high = group['High'].max()
                        daily_low = group['Low'].min()
                        daily_open = group['Open'].iloc[0]
                        
                        if daily_open > 0:  # Avoid division by zero
                            volatility = (daily_high - daily_low) / daily_open * 100
                            daily_volatility.append(volatility)
                
                # If we have volatility for at least one day, return the average
                if daily_volatility:
                    return np.mean(daily_volatility)
                
            # Not enough data, retry with different parameters
            retry_count += 1
            if retry_count >= max_retries:
                st.warning(f"Insufficient data to calculate intraday volatility for {ticker}")
                # Return a simulated intraday volatility
                if ticker in ["TSLA", "NVDA", "COIN", "GME", "AMC"]:
                    return np.random.uniform(2.5, 4.0)  # High volatility stocks
                elif ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
                    return np.random.uniform(1.5, 2.5)  # Medium volatility stocks
                else:
                    return np.random.uniform(0.8, 1.5)  # Lower volatility stocks
            time.sleep(1)
        
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.warning(f"Error calculating intraday volatility for {ticker}: {str(e)}")
                # Return a simulated intraday volatility
                if ticker in ["TSLA", "NVDA", "COIN", "GME", "AMC"]:
                    return np.random.uniform(2.5, 4.0)  # High volatility stocks
                elif ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
                    return np.random.uniform(1.5, 2.5)  # Medium volatility stocks
                else:
                    return np.random.uniform(0.8, 1.5)  # Lower volatility stocks
            time.sleep(1)

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
            
            # Try to get last close price
            stock_data = fetch_stock_data(ticker, period="2d")
            if not stock_data.empty and len(stock_data) > 1:
                last_close = stock_data['Close'].iloc[-2]
            else:
                # If we can't get historical data, use a random value
                last_close = np.random.uniform(50, 200)
            
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
        except Exception as e:
            # Skip this ticker and continue with others
            continue
    
    # Convert to DataFrame and sort by absolute change
    premarket_df = pd.DataFrame(premarket_data)
    if not premarket_df.empty:
        premarket_df['Abs Change'] = premarket_df['Pre-market Change %'].abs()
        premarket_df = premarket_df.sort_values('Abs Change', ascending=False).drop('Abs Change', axis=1)
    
    return premarket_df

def get_day_trading_metrics(ticker, max_retries=3):
    """
    Calculate key day trading metrics for a stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    max_retries (int): Maximum number of retry attempts
    
    Returns:
    dict: Dictionary of day trading metrics
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Get recent data
            daily_data = fetch_stock_data(ticker, period="10d", interval="1d")
            intraday_data = fetch_stock_data(ticker, period="5d", interval="5m")
            
            # Initialize metrics with default values
            metrics = {
                'avg_daily_range': 0.0,
                'intraday_volatility': 0.0,
                'avg_volume': 0,
                'stop_loss': 0.0,
                'profit_target': 0.0,
                'best_entry_time': "9:30 AM",
                'liquidity_score': 5
            }
            
            # If we have daily data, calculate daily metrics
            if not daily_data.empty and len(daily_data) >= 3:
                # Calculate average daily range
                daily_data['daily_range'] = daily_data['High'] - daily_data['Low']
                metrics['avg_daily_range'] = daily_data['daily_range'].mean()
                
                # Calculate average volume
                if 'Volume' in daily_data.columns:
                    metrics['avg_volume'] = daily_data['Volume'].mean()
                
                # Get current price
                current_price = daily_data['Close'].iloc[-1]
            else:
                # Use default or estimate
                current_price = 100  # Placeholder value
            
            # Calculate intraday volatility if we have intraday data
            intraday_vol = get_intraday_volatility(ticker)
            metrics['intraday_volatility'] = intraday_vol
            
            # Suggested stop loss (2x average intraday volatility)
            metrics['stop_loss'] = current_price * (1 - intraday_vol/100 * 2)
            
            # Suggested profit target (1.5x stop loss distance)
            profit_distance = current_price - metrics['stop_loss']
            metrics['profit_target'] = current_price + (profit_distance * 1.5)
            
            # Calculate typical price moves by time of day
            if not intraday_data.empty and len(intraday_data) > 20:
                # Extract hour from index
                intraday_data['hour'] = intraday_data.index.hour
                
                hourly_moves = {}
                for hour, group in intraday_data.groupby('hour'):
                    if len(group) > 5:  # Make sure we have enough data
                        hourly_moves[hour] = (group['High'].max() - group['Low'].min()) / group['Open'].iloc[0] * 100
                
                # Determine best entry time (hour with typically largest moves)
                best_entry = max(hourly_moves.items(), key=lambda x: x[1])[0] if hourly_moves else 9
                metrics['best_entry_time'] = f"{best_entry}:30 AM" if best_entry < 12 else f"{best_entry-12}:30 PM"
                
                # Calculate liquidity score (1-10 scale based on volume and spread)
                volume_score = min(10, metrics['avg_volume'] / 1000000)
                metrics['liquidity_score'] = round(volume_score)
            
            return metrics
        
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.warning(f"Error calculating day trading metrics for {ticker}: {str(e)}")
                # Return simulated metrics
                current_price = 100
                
                # Generate a more ticker-specific price for more realism
                if ticker == "AAPL": current_price = 180
                elif ticker == "MSFT": current_price = 320
                elif ticker == "GOOGL": current_price = 130
                elif ticker == "AMZN": current_price = 150
                elif ticker == "TSLA": current_price = 240
                
                # Simulate volatility based on ticker type
                intraday_vol = 1.0  # Default
                if ticker in ["TSLA", "NVDA", "COIN"]:
                    intraday_vol = np.random.uniform(2.0, 3.5)  # Higher volatility
                else:
                    intraday_vol = np.random.uniform(0.8, 2.0)  # Standard volatility
                
                # Calculate simulated stop loss and profit targets
                stop_loss = current_price * (1 - intraday_vol/100 * 2)
                profit_distance = current_price - stop_loss
                profit_target = current_price + (profit_distance * 1.5)
                
                # Best entry time - randomly select from most active hours
                active_hours = [9, 10, 14, 15]  # 9:30AM, 10:30AM, 2:30PM, 3:30PM
                best_entry = np.random.choice(active_hours)
                best_entry_time = f"{best_entry}:30 AM" if best_entry < 12 else f"{best_entry-12}:30 PM"
                
                # Liquidity score based on stock popularity
                liquidity_score = 8 if ticker in ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"] else np.random.randint(4, 7)
                
                return {
                    'avg_daily_range': current_price * intraday_vol / 100 * 2,
                    'intraday_volatility': intraday_vol,
                    'avg_volume': np.random.randint(500000, 5000000),
                    'stop_loss': stop_loss,
                    'profit_target': profit_target,
                    'best_entry_time': best_entry_time,
                    'liquidity_score': liquidity_score
                }
            time.sleep(1)  # Wait before retrying