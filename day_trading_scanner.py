#day_trading_scanner.py
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import random

from stock_data import (
    fetch_stock_data, 
    get_stock_info, 
    calculate_historical_volatility,
    get_intraday_volatility,
    get_best_day_trading_stocks,
    get_day_trading_metrics
)

from technical_analysis import calculate_technical_indicators, analyze_stock

def scan_for_day_trading_opportunities(scanner_type="Momentum Scanner", min_price=5.0, max_price=200.0, min_volume=500000):
    """
    Scan for day trading opportunities based on the selected scanner type
    
    Parameters:
    scanner_type (str): Type of scan to perform
    min_price (float): Minimum stock price
    max_price (float): Maximum stock price
    min_volume (int): Minimum daily volume
    
    Returns:
    DataFrame: DataFrame containing scan results
    """
    # In a production environment, this would use real-time market data and screening
    # For demo purposes, we'll use a curated list and add simulated metrics
    
    day_trading_candidates = get_best_day_trading_stocks()
    
    # Filter results based on the scanner type
    scan_results = []
    
    for ticker in day_trading_candidates:
        try:
            # Fetch basic stock data
            stock_data = fetch_stock_data(ticker, period="5d")
            
            if stock_data.empty:
                continue
                
            stock_info = get_stock_info(ticker)
            current_price = stock_data['Close'].iloc[-1]
            
            # Filter by price range
            if current_price < min_price or current_price > max_price:
                continue
                
            # Filter by volume
            avg_volume = stock_data['Volume'].mean()
            if avg_volume < min_volume:
                continue
                
            # Calculate change
            prev_price = stock_data['Close'].iloc[-2]
            price_change = ((current_price / prev_price) - 1) * 100
            
            # Calculate volume change
            prev_volume = stock_data['Volume'].iloc[-2]
            volume_change = ((stock_data['Volume'].iloc[-1] / prev_volume) - 1) * 100
            
            # Calculate volatility
            volatility = calculate_historical_volatility(ticker, days=10)
            
            # Perform scanner-specific checks
            scanner_match = False
            scanner_score = 0
            
            if scanner_type == "Gap Scanner":
                # Check for significant gaps
                gap_up = (stock_data['Open'].iloc[-1] - stock_data['Close'].iloc[-2]) / stock_data['Close'].iloc[-2] * 100
                if abs(gap_up) > 1.0:  # Gap of at least 1%
                    scanner_match = True
                    scanner_score = abs(gap_up)
                    
            elif scanner_type == "Momentum Scanner":
                # Check for strong directional movement
                if abs(price_change) > 2.0 and volume_change > 20:
                    scanner_match = True
                    scanner_score = abs(price_change) * (volume_change / 100)
                    
            elif scanner_type == "Volatility Scanner":
                # Check for high volatility
                intraday_volatility = get_intraday_volatility(ticker)
                if intraday_volatility > 2.0:
                    scanner_match = True
                    scanner_score = intraday_volatility
                    
            elif scanner_type == "Reversal Scanner":
                # Check for potential reversal
                rsi_data = calculate_technical_indicators(stock_data, ["RSI"])
                if "RSI" in rsi_data:
                    rsi = rsi_data["RSI"].iloc[-1]
                    if (rsi < 30 and price_change > 0) or (rsi > 70 and price_change < 0):
                        scanner_match = True
                        scanner_score = abs(rsi - 50)
            
            # Add to results if it matches the scanner criteria
            if scanner_match:
                scan_results.append({
                    'Symbol': ticker,
                    'Company': stock_info.get('name', ticker),
                    'Price': current_price,
                    'Change': price_change,
                    'Volume': stock_data['Volume'].iloc[-1],
                    'Volume % Change': volume_change,
                    'Volatility': volatility,
                    'Score': scanner_score
                })
        except Exception as e:
            st.warning(f"Error scanning {ticker}: {str(e)}")
            continue
    
    # Convert to DataFrame and sort by score
    results_df = pd.DataFrame(scan_results)
    
    if not results_df.empty:
        results_df = results_df.sort_values('Score', ascending=False)
    
    return results_df

def get_weekly_picks():
    """
    Generate weekly top picks for day trading based on technical analysis,
    volatility, and historical performance
    
    Returns:
    DataFrame: DataFrame with weekly picks and expected gains
    """
    # Get list of potential day trading stocks
    candidates = get_best_day_trading_stocks()
    
    weekly_picks = []
    
    for ticker in candidates:
        try:
            # Basic stock info
            stock_info = get_stock_info(ticker)
            
            # Get technical analysis
            stock_data = fetch_stock_data(ticker, period="1mo")
            
            if stock_data.empty:
                continue
                
            analysis_results, _ = analyze_stock(ticker, period="1mo")
            
            # Calculate volatility and day trading metrics
            volatility = calculate_historical_volatility(ticker)
            day_metrics = get_day_trading_metrics(ticker)
            
            # Calculate expected gain based on historical data and volatility
            # In a production app, this would use more sophisticated models
            expected_gain = min(25, volatility * 0.75)  # Cap at 25%
            
            # Determine optimal trading strategy
            strategy = "Momentum" if volatility > 3.0 else "Breakout" if analysis_results['recommendation'] == "Buy" else "Reversal"
            
            # Determine risk level
            if volatility > 5.0:
                risk_level = "High"
            elif volatility > 3.0:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            # Add to weekly picks
            weekly_picks.append({
                'symbol': ticker,
                'name': stock_info.get('name', ticker),
                'sector': stock_info.get('sector', 'N/A'),
                'price': stock_data['Close'].iloc[-1],
                'volatility': volatility,
                'volume': stock_data['Volume'].mean(),
                'strategy': strategy,
                'estimated_gain': round(expected_gain, 1),
                'risk_level': risk_level,
                'recommendation': analysis_results['recommendation'],
                'best_entry_time': day_metrics['best_entry_time'],
                'stop_loss': day_metrics['stop_loss'],
                'profit_target': day_metrics['profit_target']
            })
            
        except Exception as e:
            st.warning(f"Error generating weekly pick for {ticker}: {str(e)}")
            continue
    
    # Convert to DataFrame and sort by estimated gain
    picks_df = pd.DataFrame(weekly_picks)
    
    if not picks_df.empty:
        picks_df = picks_df.sort_values('estimated_gain', ascending=False)
    
    return picks_df

def get_sector_performance():
    """
    Get the performance of different sectors for sector rotation analysis
    
    Returns:
    DataFrame: DataFrame with sector performance data
    """
    # In a production app, this would use real sector ETF data
    # For demo purposes, we'll simulate sector performance
    
    sectors = [
        "Technology", "Financial", "Healthcare", "Consumer Cyclical", 
        "Energy", "Utilities", "Materials", "Industrial", 
        "Consumer Defensive", "Communication Services", "Real Estate"
    ]
    
    sector_data = []
    
    # Create simulated data for each sector
    for sector in sectors:
        daily_change = np.random.normal(0, 1.5)  # Random daily change
        weekly_change = np.random.normal(0, 3.0)  # Random weekly change
        monthly_change = np.random.normal(0, 6.0)  # Random monthly change
        
        # Simulate relative strength (1-10 scale)
        relative_strength = min(10, max(1, 5 + (monthly_change / 3)))
        
        # Determine trend
        if monthly_change > 3:
            trend = "Strong Up"
        elif monthly_change > 0:
            trend = "Up"
        elif monthly_change > -3:
            trend = "Down"
        else:
            trend = "Strong Down"
        
        sector_data.append({
            'Sector': sector,
            'Daily Change %': daily_change,
            'Weekly Change %': weekly_change,
            'Monthly Change %': monthly_change,
            'Relative Strength': round(relative_strength, 1),
            'Trend': trend
        })
    
    # Convert to DataFrame and sort by relative strength
    sector_df = pd.DataFrame(sector_data)
    sector_df = sector_df.sort_values('Relative Strength', ascending=False)
    
    return sector_df

def get_trading_opportunities_by_timeframe():
    """
    Get trading opportunities categorized by optimal trading timeframe
    
    Returns:
    dict: Dictionary containing lists of stocks by timeframe
    """
    # Get list of day trading candidates
    candidates = get_best_day_trading_stocks()
    
    # Initialize timeframe categories
    opportunities = {
        'opening_range_breakout': [],
        'midday_momentum': [],
        'power_hour': [],
        'closing_auction': []
    }
    
    # Analyze each stock to determine optimal trading timeframe
    for ticker in candidates:
        try:
            # Fetch intraday data (would be more extensive in production)
            intraday_data = fetch_stock_data(ticker, period="5d", interval="15m")
            
            if intraday_data.empty:
                continue
            
            # Group by time of day
            intraday_data['hour'] = intraday_data.index.hour
            intraday_data['minute'] = intraday_data.index.minute
            
            # Calculate price movement by time period
            # Morning (9:30-11:00)
            morning_data = intraday_data[(intraday_data['hour'] == 9) | 
                                         ((intraday_data['hour'] == 10) & (intraday_data['minute'] <= 30))]
            
            # Midday (11:00-14:00)
            midday_data = intraday_data[((intraday_data['hour'] == 10) & (intraday_data['minute'] > 30)) | 
                                        (intraday_data['hour'] == 11) | 
                                        (intraday_data['hour'] == 12) | 
                                        (intraday_data['hour'] == 13)]
            
            # Power hour (14:00-16:00)
            power_hour_data = intraday_data[(intraday_data['hour'] == 14) | (intraday_data['hour'] == 15)]
            
            # Calculate average price ranges for each period
            morning_range = 0
            midday_range = 0
            power_hour_range = 0
            
            if not morning_data.empty:
                morning_range = (morning_data.groupby(morning_data.index.date)['High'].max() - 
                                morning_data.groupby(morning_data.index.date)['Low'].min()).mean()
            
            if not midday_data.empty:
                midday_range = (midday_data.groupby(midday_data.index.date)['High'].max() - 
                               midday_data.groupby(midday_data.index.date)['Low'].min()).mean()
            
            if not power_hour_data.empty:
                power_hour_range = (power_hour_data.groupby(power_hour_data.index.date)['High'].max() - 
                                   power_hour_data.groupby(power_hour_data.index.date)['Low'].min()).mean()
            
            # Get stock info
            stock_info = get_stock_info(ticker)
            current_price = intraday_data['Close'].iloc[-1] if not intraday_data.empty else 0
            
            # Determine optimal trading timeframe
            ranges = [
                ('opening_range_breakout', morning_range),
                ('midday_momentum', midday_range),
                ('power_hour', power_hour_range)
            ]
            
            # Find the timeframe with the largest price range
            optimal_timeframe, _ = max(ranges, key=lambda x: x[1])
            
            # Randomly assign some stocks to closing auction for demo purposes
            if random.random() < 0.15:  # 15% chance
                optimal_timeframe = 'closing_auction'
            
            # Add to appropriate category
            opportunities[optimal_timeframe].append({
                'symbol': ticker,
                'name': stock_info.get('name', ticker),
                'price': current_price,
                'optimal_time': optimal_timeframe.replace('_', ' ').title()
            })
            
        except Exception as e:
            continue
    
    return opportunities