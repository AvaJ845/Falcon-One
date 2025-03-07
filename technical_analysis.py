#technical_analysis.py
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

from stock_data import fetch_stock_data, get_stock_info, get_day_trading_metrics

def calculate_technical_indicators(stock_data, indicators):
    """
    Calculate technical indicators for a given stock data
    
    Parameters:
    stock_data (DataFrame): DataFrame containing stock price data
    indicators (list): List of indicators to calculate
    
    Returns:
    dict: Dictionary of indicators and their values
    """
    results = {}
    
    # Simple Moving Averages
    if 'SMA20' in indicators:
        results['SMA20'] = stock_data['Close'].rolling(window=20).mean()
    
    if 'SMA50' in indicators:
        results['SMA50'] = stock_data['Close'].rolling(window=50).mean()
    
    if 'SMA200' in indicators:
        results['SMA200'] = stock_data['Close'].rolling(window=200).mean()
    
    # Exponential Moving Averages
    if 'EMA9' in indicators:
        results['EMA9'] = stock_data['Close'].ewm(span=9, adjust=False).mean()
    
    if 'EMA21' in indicators:
        results['EMA21'] = stock_data['Close'].ewm(span=21, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    if 'RSI' in indicators:
        delta = stock_data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        results['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (Moving Average Convergence Divergence)
    if 'MACD' in indicators:
        ema12 = stock_data['Close'].ewm(span=12, adjust=False).mean()
        ema26 = stock_data['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        
        results['MACD'] = {
            'MACD Line': macd_line,
            'Signal Line': signal_line,
            'Histogram': macd_line - signal_line
        }
    
    # Bollinger Bands
    if 'Bollinger Bands' in indicators:
        sma20 = stock_data['Close'].rolling(window=20).mean()
        std20 = stock_data['Close'].rolling(window=20).std()
        
        results['Bollinger Bands'] = {
            'Middle Band': sma20,
            'Upper Band': sma20 + (std20 * 2),
            'Lower Band': sma20 - (std20 * 2)
        }
    
    # Average True Range (ATR)
    if 'ATR' in indicators:
        high_low = stock_data['High'] - stock_data['Low']
        high_close = np.abs(stock_data['High'] - stock_data['Close'].shift())
        low_close = np.abs(stock_data['Low'] - stock_data['Close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        results['ATR'] = true_range.rolling(window=14).mean()
    
    # On-Balance Volume (OBV)
    if 'OBV' in indicators:
        obv = (np.sign(stock_data['Close'].diff()) * stock_data['Volume']).fillna(0).cumsum()
        results['OBV'] = obv
    
    # VWAP (Volume Weighted Average Price) - for intraday only
    if 'VWAP' in indicators and 'Volume' in stock_data.columns:
        # Check if this is intraday data by looking at the index frequency
        index_diff = stock_data.index[1] - stock_data.index[0]
        if index_diff < timedelta(days=1):
            # Group by date
            stock_data['Date'] = stock_data.index.date
            vwap_result = pd.Series(index=stock_data.index)
            
            for date, group in stock_data.groupby('Date'):
                cumulative_pv = ((group['High'] + group['Low'] + group['Close']) / 3 * group['Volume']).cumsum()
                cumulative_volume = group['Volume'].cumsum()
                vwap_result.loc[group.index] = cumulative_pv / cumulative_volume
            
            results['VWAP'] = vwap_result
    
    return results

def get_support_resistance(stock_data, lookback=30, step=2, threshold=0.005):
    """
    Calculate support and resistance levels
    
    Parameters:
    stock_data (DataFrame): DataFrame containing stock price data
    lookback (int): Number of days to look back
    step (int): Step size for finding levels
    threshold (float): Threshold for grouping levels (as percentage of price)
    
    Returns:
    dict: Dictionary containing support and resistance levels
    """
    # Ensure we have enough data
    if len(stock_data) < lookback:
        return {'support': [], 'resistance': []}
    
    # Get recent data
    recent_data = stock_data.tail(lookback)
    
    # Find potential levels
    highs = recent_data['High'].values
    lows = recent_data['Low'].values
    
    # Average price for threshold calculation
    avg_price = recent_data['Close'].mean()
    price_threshold = avg_price * threshold
    
    # Find local maxima for resistance
    resistance_levels = []
    for i in range(step, len(highs) - step):
        if all(highs[i] > highs[i-j] for j in range(1, step+1)) and all(highs[i] > highs[i+j] for j in range(1, step+1)):
            resistance_levels.append(highs[i])
    
    # Find local minima for support
    support_levels = []
    for i in range(step, len(lows) - step):
        if all(lows[i] < lows[i-j] for j in range(1, step+1)) and all(lows[i] < lows[i+j] for j in range(1, step+1)):
            support_levels.append(lows[i])
    
    # Group nearby levels
    grouped_resistance = group_nearby_levels(resistance_levels, price_threshold)
    grouped_support = group_nearby_levels(support_levels, price_threshold)
    
    # Sort levels
    grouped_resistance.sort(reverse=True)
    grouped_support.sort()
    
    return {
        'resistance': grouped_resistance,
        'support': grouped_support
    }

def group_nearby_levels(levels, threshold):
    """
    Group nearby price levels
    
    Parameters:
    levels (list): List of price levels
    threshold (float): Threshold for grouping levels
    
    Returns:
    list: List of grouped levels
    """
    if not levels:
        return []
    
    # Sort levels
    sorted_levels = sorted(levels)
    
    # Group nearby levels
    grouped_levels = []
    current_group = [sorted_levels[0]]
    
    for level in sorted_levels[1:]:
        if level - current_group[-1] < threshold:
            current_group.append(level)
        else:
            # Add average of current group
            grouped_levels.append(sum(current_group) / len(current_group))
            current_group = [level]
    
    # Add the last group
    if current_group:
        grouped_levels.append(sum(current_group) / len(current_group))
    
    return grouped_levels

def analyze_stock(ticker, period="1d", interval="5m"):
    """
    Analyze a stock and generate trading signals
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Time period to analyze
    interval (str): Data interval
    
    Returns:
    dict: Dictionary containing analysis results
    DataFrame: Stock data with indicators
    """
    # Fetch stock data
    stock_data = fetch_stock_data(ticker, period=period, interval=interval)
    
    if stock_data.empty:
        return {}, pd.DataFrame()
    
    # Calculate indicators
    indicators = calculate_technical_indicators(
        stock_data, 
        ['SMA20', 'SMA50', 'EMA9', 'RSI', 'MACD', 'Bollinger Bands', 'ATR']
    )
    
    # Get stock info
    stock_info = get_stock_info(ticker)
    
    # Get current and previous price
    current_price = stock_data['Close'].iloc[-1]
    prev_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else current_price
    price_change = ((current_price / prev_price) - 1) * 100
    
    # Get current volume
    current_volume = stock_data['Volume'].iloc[-1] if 'Volume' in stock_data.columns else 0
    prev_volume = stock_data['Volume'].iloc[-2] if 'Volume' in stock_data.columns and len(stock_data) > 1 else current_volume
    volume_change = ((current_volume / prev_volume) - 1) * 100 if prev_volume > 0 else 0
    
    # Calculate volatility
    if len(stock_data) >= 20:
        returns = stock_data['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility as percentage
    else:
        volatility = 0.0
    
    # Generate signals
    signals = {}
    
    # Moving Average signals
    if 'SMA20' in indicators and 'SMA50' in indicators:
        sma20 = indicators['SMA20'].iloc[-1]
        sma50 = indicators['SMA50'].iloc[-1]
        
        # Price relative to moving averages
        signals['Price vs SMA20'] = 'Buy' if current_price > sma20 else 'Sell'
        signals['Price vs SMA50'] = 'Buy' if current_price > sma50 else 'Sell'
        
        # Moving average crossover
        signals['SMA20 vs SMA50'] = 'Buy' if sma20 > sma50 else 'Sell'
    
    # RSI signals
    if 'RSI' in indicators:
        rsi = indicators['RSI'].iloc[-1]
        
        if rsi > 70:
            signals['RSI'] = 'Sell'  # Overbought
        elif rsi < 30:
            signals['RSI'] = 'Buy'   # Oversold
        else:
            signals['RSI'] = 'Neutral'
    
    # MACD signals
    if 'MACD' in indicators:
        macd_line = indicators['MACD']['MACD Line'].iloc[-1]
        signal_line = indicators['MACD']['Signal Line'].iloc[-1]
        histogram = indicators['MACD']['Histogram'].iloc[-1]
        
        if macd_line > signal_line:
            signals['MACD'] = 'Buy'
        else:
            signals['MACD'] = 'Sell'
    
    # Bollinger Band signals
    if 'Bollinger Bands' in indicators:
        upper_band = indicators['Bollinger Bands']['Upper Band'].iloc[-1]
        lower_band = indicators['Bollinger Bands']['Lower Band'].iloc[-1]
        
        if current_price > upper_band:
            signals['Bollinger Bands'] = 'Sell'  # Price above upper band
        elif current_price < lower_band:
            signals['Bollinger Bands'] = 'Buy'   # Price below lower band
        else:
            signals['Bollinger Bands'] = 'Neutral'
    
    # Generate overall recommendation
    buy_signals = sum(1 for signal in signals.values() if signal == 'Buy')
    sell_signals = sum(1 for signal in signals.values() if signal == 'Sell')
    
    if buy_signals >= sell_signals + 2:
        recommendation = 'Strong Buy'
    elif buy_signals > sell_signals:
        recommendation = 'Buy'
    elif sell_signals >= buy_signals + 2:
        recommendation = 'Strong Sell'
    elif sell_signals > buy_signals:
        recommendation = 'Sell'
    else:
        recommendation = 'Neutral'
    
    # Get day trading specific metrics
    day_trading_metrics = get_day_trading_metrics(ticker)
    
    # Compile results
    analysis_results = {
        'ticker': ticker,
        'name': stock_info.get('name', ticker),
        'current_price': current_price,
        'price_change': price_change,
        'volume': current_volume,
        'volume_change': volume_change,
        'volatility': volatility,
        'signals': signals,
        'recommendation': recommendation,
        'indicators': {k: v.iloc[-1] if isinstance(v, pd.Series) else v for k, v in indicators.items()},
        'day_trading': day_trading_metrics
    }
    
    return analysis_results, stock_data

def get_pattern_recognition(stock_data):
    """
    Identify chart patterns
    
    Parameters:
    stock_data (DataFrame): DataFrame containing stock price data
    
    Returns:
    dict: Dictionary containing identified patterns
    """
    patterns = {}
    
    # Ensure we have enough data
    if len(stock_data) < 30:
        return patterns
    
    # Get OHLC data
    closes = stock_data['Close'].values
    opens = stock_data['Open'].values
    highs = stock_data['High'].values
    lows = stock_data['Low'].values
    
    # Check for double top pattern
    for i in range(20, len(highs) - 5):
        # Find a recent high
        if (highs[i] > highs[i-1] and highs[i] > highs[i+1] and
            highs[i] > highs[i-2] and highs[i] > highs[i+2]):
            
            # Look for second high
            for j in range(i+3, min(i+15, len(highs)-1)):
                if (abs(highs[j] - highs[i]) / highs[i] < 0.02 and  # Within 2% of first high
                    highs[j] > highs[j-1] and highs[j] > highs[j+1]):
                    
                    # Check for minimum drop between peaks
                    min_between = min(closes[i+1:j])
                    if (highs[i] - min_between) / highs[i] > 0.03:  # At least 3% drop between peaks
                        patterns['Double Top'] = {
                            'start_idx': i,
                            'end_idx': j,
                            'pattern_type': 'bearish',
                            'confidence': 'high'
                        }
                        break
    
    # Check for double bottom pattern
    for i in range(20, len(lows) - 5):
        # Find a recent low
        if (lows[i] < lows[i-1] and lows[i] < lows[i+1] and
            lows[i] < lows[i-2] and lows[i] < lows[i+2]):
            
            # Look for second low
            for j in range(i+3, min(i+15, len(lows)-1)):
                if (abs(lows[j] - lows[i]) / lows[i] < 0.02 and  # Within 2% of first low
                    lows[j] < lows[j-1] and lows[j] < lows[j+1]):
                    
                    # Check for minimum rise between troughs
                    max_between = max(closes[i+1:j])
                    if (max_between - lows[i]) / lows[i] > 0.03:  # At least 3% rise between troughs
                        patterns['Double Bottom'] = {
                            'start_idx': i,
                            'end_idx': j,
                            'pattern_type': 'bullish',
                            'confidence': 'high'
                        }
                        break
    
    # Check for head and shoulders pattern (basic version)
    for i in range(20, len(highs) - 15):
        # Left shoulder
        if (highs[i] > highs[i-1] and highs[i] > highs[i+1]):
            # Look for head
            head_idx = -1
            for j in range(i+2, i+10):
                if j >= len(highs):
                    break
                if (highs[j] > highs[j-1] and highs[j] > highs[j+1] and highs[j] > highs[i]):
                    head_idx = j
                    break
            
            # Look for right shoulder
            if head_idx > 0:
                for k in range(head_idx+2, head_idx+10):
                    if k >= len(highs):
                        break
                    if (highs[k] > highs[k-1] and highs[k] > highs[k+1] and 
                        abs(highs[k] - highs[i]) / highs[i] < 0.05):  # Right shoulder similar to left
                        
                        patterns['Head and Shoulders'] = {
                            'start_idx': i,
                            'end_idx': k,
                            'pattern_type': 'bearish',
                            'confidence': 'medium'
                        }
                        break
    
    # Doji patterns (single candlestick)
    for i in range(len(opens) - 1, max(len(opens) - 5, 0), -1):
        body_size = abs(closes[i] - opens[i])
        wick_size = highs[i] - max(closes[i], opens[i])
        tail_size = min(closes[i], opens[i]) - lows[i]
        
        # Doji (open and close very close)
        if body_size / ((highs[i] - lows[i]) or 1) < 0.1:
            patterns['Doji'] = {
                'index': i,
                'pattern_type': 'neutral',
                'confidence': 'medium'
            }
            break
        
        # Hammer (small body, long lower tail, little or no upper wick)
        elif (body_size / ((highs[i] - lows[i]) or 1) < 0.3 and
              tail_size > 2 * body_size and
              wick_size < 0.5 * body_size):
            patterns['Hammer'] = {
                'index': i,
                'pattern_type': 'bullish',
                'confidence': 'medium'
            }
            break
    
    return patterns

def get_stock_technical_score(ticker):
    """
    Generate a composite technical score for a stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    
    Returns:
    dict: Dictionary containing technical score and breakdown
    """
    try:
        # Fetch data for different timeframes
        daily_data = fetch_stock_data(ticker, period="3mo", interval="1d")
        intraday_data = fetch_stock_data(ticker, period="5d", interval="15m")
        
        if daily_data.empty:
            return {'overall_score': 50}
        
        # Calculate indicators for daily timeframe
        daily_indicators = calculate_technical_indicators(
            daily_data, 
            ['SMA20', 'SMA50', 'SMA200', 'RSI', 'MACD', 'Bollinger Bands']
        )
        
        # Calculate scores for each indicator (0-100 scale)
        scores = {}
        
        # Trend score
        trend_score = 50
        if 'SMA20' in daily_indicators and 'SMA50' in daily_indicators and 'SMA200' in daily_indicators:
            price = daily_data['Close'].iloc[-1]
            sma20 = daily_indicators['SMA20'].iloc[-1]
            sma50 = daily_indicators['SMA50'].iloc[-1]
            sma200 = daily_indicators['SMA200'].iloc[-1]
            
            # Strong uptrend
            if price > sma20 > sma50 > sma200:
                trend_score = 90
            # Uptrend
            elif price > sma20 and price > sma50:
                trend_score = 75
            # Weak uptrend
            elif price > sma20:
                trend_score = 60
            # Weak downtrend
            elif price < sma20:
                trend_score = 40
            # Downtrend
            elif price < sma20 and price < sma50:
                trend_score = 25
            # Strong downtrend
            elif price < sma20 < sma50 < sma200:
                trend_score = 10
        
        scores['trend'] = trend_score
        
        # Momentum score
        momentum_score = 50
        if 'RSI' in daily_indicators:
            rsi = daily_indicators['RSI'].iloc[-1]
            
            if rsi > 70:
                momentum_score = 80  # Strong momentum but overbought
            elif rsi > 60:
                momentum_score = 70  # Good momentum
            elif rsi > 50:
                momentum_score = 60  # Positive momentum
            elif rsi > 40:
                momentum_score = 40  # Negative momentum
            elif rsi > 30:
                momentum_score = 30  # Weak momentum
            else:
                momentum_score = 20  # Very weak momentum but oversold
        
        scores['momentum'] = momentum_score
        
        # MACD score
        macd_score = 50
        if 'MACD' in daily_indicators:
            macd_line = daily_indicators['MACD']['MACD Line'].iloc[-1]
            signal_line = daily_indicators['MACD']['Signal Line'].iloc[-1]
            histogram = daily_indicators['MACD']['Histogram'].iloc[-1]
            
            if macd_line > signal_line and histogram > 0:
                # Bullish MACD
                macd_score = 70
                
                # Check if MACD is increasing
                if len(daily_indicators['MACD']['Histogram']) > 1:
                    prev_histogram = daily_indicators['MACD']['Histogram'].iloc[-2]
                    if histogram > prev_histogram:
                        macd_score = 80  # Strengthening bullish momentum
            elif macd_line < signal_line and histogram < 0:
                # Bearish MACD
                macd_score = 30
                
                # Check if MACD is decreasing
                if len(daily_indicators['MACD']['Histogram']) > 1:
                    prev_histogram = daily_indicators['MACD']['Histogram'].iloc[-2]
                    if histogram < prev_histogram:
                        macd_score = 20  # Strengthening bearish momentum
        
        scores['macd'] = macd_score
        
        # Volatility score (higher volatility = higher day trading potential)
        volatility_score = 50
        if 'Bollinger Bands' in daily_indicators:
            middle = daily_indicators['Bollinger Bands']['Middle Band'].iloc[-1]
            upper = daily_indicators['Bollinger Bands']['Upper Band'].iloc[-1]
            
            # Calculate Bollinger Band width as percentage of price
            bb_width = (upper - middle) / middle * 100
            
            if bb_width > 4:
                volatility_score = 80  # High volatility
            elif bb_width > 3:
                volatility_score = 70  # Above average volatility
            elif bb_width > 2:
                volatility_score = 60  # Average volatility
            elif bb_width > 1.5:
                volatility_score = 40  # Below average volatility
            else:
                volatility_score = 30  # Low volatility
        
        scores['volatility'] = volatility_score
        
        # Volume score
        volume_score = 50
        if 'Volume' in daily_data.columns and len(daily_data) > 20:
            recent_volume = daily_data['Volume'].iloc[-1]
            avg_volume = daily_data['Volume'].rolling(window=20).mean().iloc[-1]
            
            if recent_volume > avg_volume * 2:
                volume_score = 90  # Very high volume
            elif recent_volume > avg_volume * 1.5:
                volume_score = 80  # High volume
            elif recent_volume > avg_volume * 1.2:
                volume_score = 70  # Above average volume
            elif recent_volume > avg_volume * 0.8:
                volume_score = 50  # Average volume
            elif recent_volume > avg_volume * 0.5:
                volume_score = 30  # Low volume
            else:
                volume_score = 20  # Very low volume
        
        scores['volume'] = volume_score
        
        # Intraday score (only if intraday data is available)
        intraday_score = 50
        if not intraday_data.empty and len(intraday_data) > 20:
            # Calculate intraday volatility
            intraday_data['range_pct'] = (intraday_data['High'] - intraday_data['Low']) / intraday_data['Open'] * 100
            avg_intraday_range = intraday_data['range_pct'].mean()
            
            if avg_intraday_range > 2:
                intraday_score = 90  # Very high intraday movement
            elif avg_intraday_range > 1.5:
                intraday_score = 80  # High intraday movement
            elif avg_intraday_range > 1:
                intraday_score = 70  # Good intraday movement
            elif avg_intraday_range > 0.7:
                intraday_score = 60  # Above average movement
            elif avg_intraday_range > 0.5:
                intraday_score = 50  # Average movement
            elif avg_intraday_range > 0.3:
                intraday_score = 40  # Below average movement
            else:
                intraday_score = 30  # Low intraday movement
        
        scores['intraday'] = intraday_score
        
        # Calculate overall technical score
        weights = {
            'trend': 0.25,
            'momentum': 0.15,
            'macd': 0.15,
            'volatility': 0.15,
            'volume': 0.15,
            'intraday': 0.15
        }
        
        overall_score = sum(scores.get(k, 50) * v for k, v in weights.items())
        
        # Determine day trading rating
        if overall_score >= 80:
            rating = "Excellent"
        elif overall_score >= 70:
            rating = "Good"
        elif overall_score >= 60:
            rating = "Above Average"
        elif overall_score >= 40:
            rating = "Average"
        elif overall_score >= 30:
            rating = "Below Average"
        else:
            rating = "Poor"
        
        return {
            'overall_score': overall_score,
            'rating': rating,
            'breakdown': scores
        }
    
    except Exception as e:
        st.warning(f"Error calculating technical score for {ticker}: {str(e)}")
        return {'overall_score': 50, 'rating': 'Average', 'breakdown': {}}