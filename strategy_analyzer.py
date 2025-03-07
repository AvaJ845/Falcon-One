#strategy_analyzer.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from stock_data import fetch_stock_data

def backtest_strategy(ticker, strategy_type, start_date, end_date, strategy_params, risk_params, use_mock_data=False):
    """
    Backtest a trading strategy on historical data
    
    Parameters:
    ticker (str): Stock ticker symbol
    strategy_type (str): Type of strategy to backtest
    start_date (str): Start date for backtesting (YYYY-MM-DD)
    end_date (str): End date for backtesting (YYYY-MM-DD)
    strategy_params (dict): Strategy-specific parameters
    risk_params (dict): Risk management parameters
    use_mock_data (bool): If True, use mock data instead of real data
    
    Returns:
    dict: Backtesting results
    """
    try:
        # Fetch historical data
        stock_data = fetch_stock_data(
            ticker, 
            interval="15m",
            start=start_date,
            end=end_date,
            use_mock_data=use_mock_data
        )
        
        if stock_data.empty:
            st.error(f"Could not fetch sufficient data for {ticker}")
            return None
        
        # Add date column for grouping
        stock_data['date'] = stock_data.index.date
        
        # Initialize results
        trades = []
        cash = 100000  # Starting capital
        position = 0   # Current position (number of shares)
        entry_price = 0  # Entry price for position
        
        # Apply the selected strategy
        if strategy_type == "Moving Average Crossover":
            results = backtest_ma_crossover(
                stock_data,
                strategy_params,
                risk_params,
                initial_cash=cash
            )
            
        elif strategy_type == "RSI Reversal":
            results = backtest_rsi_reversal(
                stock_data,
                strategy_params,
                risk_params,
                initial_cash=cash
            )
            
        elif strategy_type == "VWAP Bounce":
            results = backtest_vwap_bounce(
                stock_data,
                strategy_params,
                risk_params,
                initial_cash=cash
            )
            
        elif strategy_type == "Breakout":
            results = backtest_breakout(
                stock_data,
                strategy_params,
                risk_params,
                initial_cash=cash
            )
            
        elif strategy_type == "Gap and Go":
            results = backtest_gap_and_go(
                stock_data,
                strategy_params,
                risk_params,
                initial_cash=cash
            )
        
        else:
            st.error(f"Strategy '{strategy_type}' not implemented")
            return None
        
        # Add strategy parameters to results
        results['strategy'] = strategy_type
        results['ticker'] = ticker
        results['start_date'] = start_date
        results['end_date'] = end_date
        results['strategy_params'] = strategy_params
        results['risk_params'] = risk_params
        
        return results
        
    except Exception as e:
        st.error(f"Error during backtesting: {str(e)}")
        return None

def calculate_equity_curve(trades, initial_cash):
    """
    Calculate the equity curve from a list of trades
    
    Parameters:
    trades (list): List of trades
    initial_cash (float): Initial capital
    
    Returns:
    DataFrame: DataFrame with equity curve
    """
    if not trades:
        return pd.DataFrame(columns=['date', 'equity'])
    
    # Initialize equity curve
    equity_points = []
    current_equity = initial_cash
    
    for trade in trades:
        if trade['type'] == 'buy':
            current_equity -= trade['value']
        elif trade['type'] == 'sell':
            current_equity += trade['value']
            if 'pnl' in trade:
                current_equity += trade['pnl']
        
        equity_points.append({
            'date': trade['date'],
            'equity': current_equity
        })
    
    # Convert to DataFrame
    equity_curve = pd.DataFrame(equity_points)
    
    # Ensure date is datetime
    if 'date' in equity_curve.columns:
        equity_curve['date'] = pd.to_datetime(equity_curve['date'])
    
        # Sort by date
        equity_curve = equity_curve.sort_values('date')
    
    return equity_curve
def backtest_ma_crossover(stock_data, strategy_params, risk_params, initial_cash=100000):
    """
    Backtest Moving Average Crossover strategy
    
    Parameters:
    stock_data (DataFrame): Historical stock data
    strategy_params (dict): Strategy parameters
    risk_params (dict): Risk management parameters
    initial_cash (float): Initial capital
    
    Returns:
    dict: Backtesting results
    """
    # Extract strategy parameters
    fast_period = strategy_params.get('fast_period', 9)
    slow_period = strategy_params.get('slow_period', 21)
    
    # Extract risk parameters
    stop_loss_pct = risk_params.get('stop_loss', 2.0) / 100
    take_profit_pct = risk_params.get('take_profit', 5.0) / 100
    position_size_pct = risk_params.get('position_size', 10) / 100
    
    # Calculate moving averages
    stock_data['fast_ma'] = stock_data['Close'].rolling(window=fast_period).mean()
    stock_data['slow_ma'] = stock_data['Close'].rolling(window=slow_period).mean()
    
    # Initialize variables
    cash = initial_cash
    shares = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    
    # Loop through data
    for i in range(max(fast_period, slow_period) + 1, len(stock_data)):
        current_bar = stock_data.iloc[i]
        prev_bar = stock_data.iloc[i-1]
        
        # Calculate signals
        fast_ma_current = current_bar['fast_ma']
        slow_ma_current = current_bar['slow_ma']
        fast_ma_prev = prev_bar['fast_ma']
        slow_ma_prev = prev_bar['slow_ma']
        
        # Buy signal: fast MA crosses above slow MA
        buy_signal = fast_ma_prev <= slow_ma_prev and fast_ma_current > slow_ma_current
        
        # Sell signal: fast MA crosses below slow MA
        sell_signal = fast_ma_prev >= slow_ma_prev and fast_ma_current < slow_ma_current
        
        # Execute buy signal if we're not already in a position
        if buy_signal and shares == 0:
            price = current_bar['Close']
            position_value = cash * position_size_pct
            shares = int(position_value / price)
            
            if shares > 0:
                cash -= shares * price
                entry_price = price
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
                
                trades.append({
                    'type': 'buy',
                    'date': current_bar.name,
                    'price': price,
                    'shares': shares,
                    'value': shares * price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                })
        
        # Execute sell signal if we're in a position
        elif (sell_signal or current_bar['Low'] <= stop_loss or current_bar['High'] >= take_profit) and shares > 0:
            price = current_bar['Close']
            
            # Use stop loss or take profit price if hit
            if current_bar['Low'] <= stop_loss:
                price = stop_loss
            elif current_bar['High'] >= take_profit:
                price = take_profit
            
            cash += shares * price
            
            # Calculate P&L
            pnl = shares * (price - entry_price)
            pnl_pct = (price / entry_price - 1) * 100
            
            trades.append({
                'type': 'sell',
                'date': current_bar.name,
                'price': price,
                'shares': shares,
                'value': shares * price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            shares = 0
            entry_price = 0
            stop_loss = 0
            take_profit = 0
    
    # Close any open position at the end of the backtest
    if shares > 0:
        last_bar = stock_data.iloc[-1]
        price = last_bar['Close']
        
        cash += shares * price
        
        # Calculate P&L
        pnl = shares * (price - entry_price)
        pnl_pct = (price / entry_price - 1) * 100
        
        trades.append({
            'type': 'sell',
            'date': last_bar.name,
            'price': price,
            'shares': shares,
            'value': shares * price,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
    
    # Calculate performance metrics
    equity = cash
    
    # Process trades for performance tracking
    buy_trades = []
    sell_trades = []
    completed_trades = []
    
    for trade in trades:
        if trade['type'] == 'buy':
            buy_trades.append(trade)
        elif trade['type'] == 'sell':
            sell_trades.append(trade)
            
            # Match with buy trade
            if buy_trades:
                buy_trade = buy_trades.pop(0)
                
                completed_trades.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'shares': trade['shares'],
                    'pnl': trade['pnl'],
                    'pnl_pct': trade['pnl_pct']
                })
    
    # Calculate returns
    total_return = (equity / initial_cash - 1) * 100
    
    # Calculate win rate
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    # Calculate average metrics
    avg_profit = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in completed_trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
    
    # Create equity curve
    equity_curve = calculate_equity_curve(trades, initial_cash)
    
    return {
        'final_equity': equity,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'trades': trades,
        'completed_trades': completed_trades,
        'equity_curve': equity_curve
    }

def backtest_rsi_reversal(stock_data, strategy_params, risk_params, initial_cash=100000):
    """
    Backtest RSI Reversal strategy
    
    Parameters:
    stock_data (DataFrame): Historical stock data
    strategy_params (dict): Strategy parameters
    risk_params (dict): Risk management parameters
    initial_cash (float): Initial capital
    
    Returns:
    dict: Backtesting results
    """
    # Extract strategy parameters
    rsi_period = strategy_params.get('rsi_period', 14)
    overbought = strategy_params.get('overbought', 70)
    oversold = strategy_params.get('oversold', 30)
    
    # Extract risk parameters
    stop_loss_pct = risk_params.get('stop_loss', 2.0) / 100
    take_profit_pct = risk_params.get('take_profit', 5.0) / 100
    position_size_pct = risk_params.get('position_size', 10) / 100
    
    # Calculate RSI
    delta = stock_data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()
    
    rs = avg_gain / avg_loss
    stock_data['RSI'] = 100 - (100 / (1 + rs))
    
    # Initialize variables
    cash = initial_cash
    shares = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    
    # Loop through data
    for i in range(rsi_period + 1, len(stock_data)):
        current_bar = stock_data.iloc[i]
        prev_bar = stock_data.iloc[i-1]
        
        # Calculate signals
        current_rsi = current_bar['RSI']
        prev_rsi = prev_bar['RSI']
        
        # Buy signal: RSI crosses above oversold level
        buy_signal = prev_rsi <= oversold and current_rsi > oversold
        
        # Sell signal: RSI crosses below overbought level
        sell_signal = prev_rsi >= overbought and current_rsi < overbought
        
        # Execute buy signal if we're not already in a position
        if buy_signal and shares == 0:
            price = current_bar['Close']
            position_value = cash * position_size_pct
            shares = int(position_value / price)
            
            if shares > 0:
                cash -= shares * price
                entry_price = price
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
                
                trades.append({
                    'type': 'buy',
                    'date': current_bar.name,
                    'price': price,
                    'shares': shares,
                    'value': shares * price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                })
        
        # Execute sell signal if we're in a position
        elif (sell_signal or current_bar['Low'] <= stop_loss or current_bar['High'] >= take_profit) and shares > 0:
            price = current_bar['Close']
            
            # Use stop loss or take profit price if hit
            if current_bar['Low'] <= stop_loss:
                price = stop_loss
            elif current_bar['High'] >= take_profit:
                price = take_profit
            
            cash += shares * price
            
            # Calculate P&L
            pnl = shares * (price - entry_price)
            pnl_pct = (price / entry_price - 1) * 100
            
            trades.append({
                'type': 'sell',
                'date': current_bar.name,
                'price': price,
                'shares': shares,
                'value': shares * price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            shares = 0
            entry_price = 0
            stop_loss = 0
            take_profit = 0
    
    # Close any open position at the end of the backtest
    if shares > 0:
        last_bar = stock_data.iloc[-1]
        price = last_bar['Close']
        
        cash += shares * price
        
        # Calculate P&L
        pnl = shares * (price - entry_price)
        pnl_pct = (price / entry_price - 1) * 100
        
        trades.append({
            'type': 'sell',
            'date': last_bar.name,
            'price': price,
            'shares': shares,
            'value': shares * price,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
    
    # Calculate performance metrics as before
    equity = cash
    
    # Process trades for performance tracking
    buy_trades = []
    sell_trades = []
    completed_trades = []
    
    for trade in trades:
        if trade['type'] == 'buy':
            buy_trades.append(trade)
        elif trade['type'] == 'sell':
            sell_trades.append(trade)
            
            # Match with buy trade
            if buy_trades:
                buy_trade = buy_trades.pop(0)
                
                completed_trades.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'shares': trade['shares'],
                    'pnl': trade['pnl'],
                    'pnl_pct': trade['pnl_pct']
                })
    
    # Calculate statistics
    total_return = (equity / initial_cash - 1) * 100
    
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    avg_profit = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in completed_trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
    
    # Create equity curve
    equity_curve = calculate_equity_curve(trades, initial_cash)
    
    return {
        'final_equity': equity,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'trades': trades,
        'completed_trades': completed_trades,
        'equity_curve': equity_curve
    }
def backtest_vwap_bounce(stock_data, strategy_params, risk_params, initial_cash=100000):
    """
    Backtest VWAP Bounce strategy
    
    Parameters:
    stock_data (DataFrame): Historical stock data
    strategy_params (dict): Strategy parameters
    risk_params (dict): Risk management parameters
    initial_cash (float): Initial capital
    
    Returns:
    dict: Backtesting results
    """
    # Extract strategy parameters
    vwap_deviation = strategy_params.get('vwap_deviation', 1.0) / 100
    
    # Extract risk parameters
    stop_loss_pct = risk_params.get('stop_loss', 2.0) / 100
    take_profit_pct = risk_params.get('take_profit', 5.0) / 100
    position_size_pct = risk_params.get('position_size', 10) / 100
    
    # Calculate VWAP for each day
    stock_data['date'] = stock_data.index.date
    
    # Group by date and calculate VWAP
    vwap_values = []
    
    for date, group in stock_data.groupby('date'):
        # Calculate typical price
        typical_price = (group['High'] + group['Low'] + group['Close']) / 3
        
        # Calculate cumulative (price * volume)
        cumulative_pv = (typical_price * group['Volume']).cumsum()
        
        # Calculate cumulative volume
        cumulative_volume = group['Volume'].cumsum()
        
        # Calculate VWAP
        vwap = cumulative_pv / cumulative_volume
        
        # Add to list
        for idx, vwap_val in zip(group.index, vwap.values):
            vwap_values.append((idx, vwap_val))
    
    # Convert to DataFrame
    vwap_df = pd.DataFrame(vwap_values, columns=['index', 'VWAP'])
    vwap_df.set_index('index', inplace=True)
    
    # Merge VWAP values back to original DataFrame
    stock_data = stock_data.join(vwap_df)
    
    # Initialize variables
    cash = initial_cash
    shares = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    
    # Loop through data
    for i in range(1, len(stock_data)):
        current_bar = stock_data.iloc[i]
        prev_bar = stock_data.iloc[i-1]
        
        if pd.isnull(current_bar['VWAP']):
            continue
        
        # Calculate price distance from VWAP
        vwap_distance = (current_bar['Close'] - current_bar['VWAP']) / current_bar['VWAP']
        
        # Buy signal: Price bounces up from below VWAP
        buy_signal = (prev_bar['Close'] < prev_bar['VWAP'] and 
                      current_bar['Close'] > current_bar['VWAP'] and 
                      abs(vwap_distance) <= vwap_deviation)
        
        # Sell signal: Price bounces down from above VWAP
        sell_signal = (prev_bar['Close'] > prev_bar['VWAP'] and 
                       current_bar['Close'] < current_bar['VWAP'] and 
                       abs(vwap_distance) <= vwap_deviation)
        
        # Execute buy signal if we're not already in a position
        if buy_signal and shares == 0:
            price = current_bar['Close']
            position_value = cash * position_size_pct
            shares = int(position_value / price)
            
            if shares > 0:
                cash -= shares * price
                entry_price = price
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
                
                trades.append({
                    'type': 'buy',
                    'date': current_bar.name,
                    'price': price,
                    'shares': shares,
                    'value': shares * price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                })
        
        # Execute sell signal if we're in a position
        elif (sell_signal or current_bar['Low'] <= stop_loss or current_bar['High'] >= take_profit) and shares > 0:
            price = current_bar['Close']
            
            # Use stop loss or take profit price if hit
            if current_bar['Low'] <= stop_loss:
                price = stop_loss
            elif current_bar['High'] >= take_profit:
                price = take_profit
            
            cash += shares * price
            
            # Calculate P&L
            pnl = shares * (price - entry_price)
            pnl_pct = (price / entry_price - 1) * 100
            
            trades.append({
                'type': 'sell',
                'date': current_bar.name,
                'price': price,
                'shares': shares,
                'value': shares * price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            shares = 0
            entry_price = 0
            stop_loss = 0
            take_profit = 0
    
    # Close any open position at the end of the backtest
    if shares > 0:
        last_bar = stock_data.iloc[-1]
        price = last_bar['Close']
        
        cash += shares * price
        
        # Calculate P&L
        pnl = shares * (price - entry_price)
        pnl_pct = (price / entry_price - 1) * 100
        
        trades.append({
            'type': 'sell',
            'date': last_bar.name,
            'price': price,
            'shares': shares,
            'value': shares * price,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
    
    # Calculate performance metrics (same as above)
    equity = cash
    
    # Process trades for performance tracking
    buy_trades = []
    sell_trades = []
    completed_trades = []
    
    for trade in trades:
        if trade['type'] == 'buy':
            buy_trades.append(trade)
        elif trade['type'] == 'sell':
            sell_trades.append(trade)
            
            # Match with buy trade
            if buy_trades:
                buy_trade = buy_trades.pop(0)
                
                completed_trades.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'shares': trade['shares'],
                    'pnl': trade['pnl'],
                    'pnl_pct': trade['pnl_pct']
                })
    
    # Calculate statistics
    total_return = (equity / initial_cash - 1) * 100
    
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    avg_profit = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in completed_trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
    
    # Create equity curve
    equity_curve = calculate_equity_curve(trades, initial_cash)
    
    return {
        'final_equity': equity,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'trades': trades,
        'completed_trades': completed_trades,
        'equity_curve': equity_curve
    }

def backtest_breakout(stock_data, strategy_params, risk_params, initial_cash=100000):
    """
    Backtest Breakout strategy
    
    Parameters:
    stock_data (DataFrame): Historical stock data
    strategy_params (dict): Strategy parameters
    risk_params (dict): Risk management parameters
    initial_cash (float): Initial capital
    
    Returns:
    dict: Backtesting results
    """
    # Extract strategy parameters
    breakout_period = strategy_params.get('breakout_period', 5)
    volume_factor = strategy_params.get('volume_factor', 2.0)
    
    # Extract risk parameters
    stop_loss_pct = risk_params.get('stop_loss', 2.0) / 100
    take_profit_pct = risk_params.get('take_profit', 5.0) / 100
    position_size_pct = risk_params.get('position_size', 10) / 100
    
    # Calculate breakout levels
    stock_data['highest_high'] = stock_data['High'].rolling(window=breakout_period).max()
    stock_data['lowest_low'] = stock_data['Low'].rolling(window=breakout_period).min()
    
    # Calculate average volume
    stock_data['avg_volume'] = stock_data['Volume'].rolling(window=breakout_period).mean()
    
    # Initialize variables
    cash = initial_cash
    shares = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    
    # Loop through data
    for i in range(breakout_period + 1, len(stock_data)):
        current_bar = stock_data.iloc[i]
        prev_bar = stock_data.iloc[i-1]
        
        # Calculate signals
        # Bullish breakout: price breaks above highest high with increased volume
        bullish_breakout = (current_bar['Close'] > prev_bar['highest_high'] and 
                           current_bar['Volume'] > prev_bar['avg_volume'] * volume_factor)
        
        # Bearish breakout: price breaks below lowest low with increased volume
        bearish_breakout = (current_bar['Close'] < prev_bar['lowest_low'] and 
                           current_bar['Volume'] > prev_bar['avg_volume'] * volume_factor)
        
        # Execute buy signal if we're not already in a position
        if bullish_breakout and shares == 0:
            price = current_bar['Close']
            position_value = cash * position_size_pct
            shares = int(position_value / price)
            
            if shares > 0 :
                cash -= shares * price
                entry_price = price
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
                
                trades.append({
                    'type': 'buy',
                    'date': current_bar.name,
                    'price': price,
                    'shares': shares,
                    'value': shares * price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                })
        
        # Execute sell signal if we're in a position
        elif (bearish_breakout or current_bar['Low'] <= stop_loss or current_bar['High'] >= take_profit) and shares > 0:
            price = current_bar['Close']
            
            # Use stop loss or take profit price if hit
            if current_bar['Low'] <= stop_loss:
                price = stop_loss
            elif current_bar['High'] >= take_profit:
                price = take_profit
            
            cash += shares * price
            
            # Calculate P&L
            pnl = shares * (price - entry_price)
            pnl_pct = (price / entry_price - 1) * 100
            
            trades.append({
                'type': 'sell',
                'date': current_bar.name,
                'price': price,
                'shares': shares,
                'value': shares * price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            shares = 0
            entry_price = 0
            stop_loss = 0
            take_profit = 0
    
    # Close any open position at the end of the backtest
    if shares > 0:
        last_bar = stock_data.iloc[-1]
        price = last_bar['Close']
        
        cash += shares * price
        
        # Calculate P&L
        pnl = shares * (price - entry_price)
        pnl_pct = (price / entry_price - 1) * 100
        
        trades.append({
            'type': 'sell',
            'date': last_bar.name,
            'price': price,
            'shares': shares,
            'value': shares * price,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
    
    # Calculate performance metrics (same as above)
    equity = cash
    
    # Process trades for performance tracking
    buy_trades = []
    sell_trades = []
    completed_trades = []
    
    for trade in trades:
        if trade['type'] == 'buy':
            buy_trades.append(trade)
        elif trade['type'] == 'sell':
            sell_trades.append(trade)
            
            # Match with buy trade
            if buy_trades:
                buy_trade = buy_trades.pop(0)
                
                completed_trades.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'shares': trade['shares'],
                    'pnl': trade['pnl'],
                    'pnl_pct': trade['pnl_pct']
                })
    
    # Calculate statistics
    total_return = (equity / initial_cash - 1) * 100
    
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    avg_profit = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in completed_trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
    
    # Create equity curve
    equity_curve = calculate_equity_curve(trades, initial_cash)
    
    return {
        'final_equity': equity,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'trades': trades,
        'completed_trades': completed_trades,
        'equity_curve': equity_curve
    }
def backtest_gap_and_go(stock_data, strategy_params, risk_params, initial_cash=100000):
    """
    Backtest Gap and Go strategy
    
    Parameters:
    stock_data (DataFrame): Historical stock data
    strategy_params (dict): Strategy parameters
    risk_params (dict): Risk management parameters
    initial_cash (float): Initial capital
    
    Returns:
    dict: Backtesting results
    """
    # Extract strategy parameters
    min_gap = strategy_params.get('min_gap', 1.0) / 100
    entry_time = strategy_params.get('entry_time', '10 min')
    
    # Extract risk parameters
    stop_loss_pct = risk_params.get('stop_loss', 2.0) / 100
    take_profit_pct = risk_params.get('take_profit', 5.0) / 100
    position_size_pct = risk_params.get('position_size', 10) / 100
    
    # Convert entry time to number of bars
    entry_bars = int(entry_time.split()[0])
    
    # Add date column for grouping
    stock_data['date'] = stock_data.index.date
    
    # Group by date
    date_groups = stock_data.groupby('date')
    
    # Initialize variables
    cash = initial_cash
    shares = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    
    prev_close = None
    
    # Process each trading day
    for date, group in date_groups:
        # Skip if not enough data
        if len(group) < entry_bars + 1:
            continue
        
        # Get opening price
        open_price = group['Open'].iloc[0]
        
        # Skip first day (no previous close)
        if prev_close is None:
            prev_close = group['Close'].iloc[-1]
            continue
        
        # Calculate gap percentage
        gap_pct = (open_price - prev_close) / prev_close
        
        # Check for significant gap
        if abs(gap_pct) >= min_gap:
            # Gap up strategy
            if gap_pct > 0:
                # Wait for entry_bars bars
                entry_bar = group.iloc[entry_bars]
                
                # Enter long position if price is still above open
                if entry_bar['Close'] > open_price and shares == 0:
                    price = entry_bar['Close']
                    position_value = cash * position_size_pct
                    shares = int(position_value / price)
                    
                    if shares > 0:
                        cash -= shares * price
                        entry_price = price
                        stop_loss = price * (1 - stop_loss_pct)
                        take_profit = price * (1 + take_profit_pct)
                        
                        trades.append({
                            'type': 'buy',
                            'date': entry_bar.name,
                            'price': price,
                            'shares': shares,
                            'value': shares * price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit
                        })
            
            # Gap down strategy (short selling not implemented in this demo)
        
        # Check for exit conditions
        if shares > 0:
            for i in range(len(group)):
                if i <= entry_bars:  # Skip bars before entry
                    continue
                
                current_bar = group.iloc[i]
                
                # Check stop loss and take profit
                if current_bar['Low'] <= stop_loss or current_bar['High'] >= take_profit:
                    price = current_bar['Close']
                    
                    # Use stop loss or take profit price if hit
                    if current_bar['Low'] <= stop_loss:
                        price = stop_loss
                    elif current_bar['High'] >= take_profit:
                        price = take_profit
                    
                    cash += shares * price
                    
                    # Calculate P&L
                    pnl = shares * (price - entry_price)
                    pnl_pct = (price / entry_price - 1) * 100
                    
                    trades.append({
                        'type': 'sell',
                        'date': current_bar.name,
                        'price': price,
                        'shares': shares,
                        'value': shares * price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
                    
                    shares = 0
                    entry_price = 0
                    stop_loss = 0
                    take_profit = 0
                    break
        
        # Close any position at end of day if still open
        if shares > 0:
            last_bar = group.iloc[-1]
            price = last_bar['Close']
            
            cash += shares * price
            
            # Calculate P&L
            pnl = shares * (price - entry_price)
            pnl_pct = (price / entry_price - 1) * 100
            
            trades.append({
                'type': 'sell',
                'date': last_bar.name,
                'price': price,
                'shares': shares,
                'value': shares * price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            shares = 0
            entry_price = 0
            stop_loss = 0
            take_profit = 0
        
        # Update previous close
        prev_close = group['Close'].iloc[-1]
    
    # Calculate performance metrics (same as above)
    equity = cash
    
    # Process trades for performance tracking
    buy_trades = []
    sell_trades = []
    completed_trades = []
    
    for trade in trades:
        if trade['type'] == 'buy':
            buy_trades.append(trade)
        elif trade['type'] == 'sell':
            sell_trades.append(trade)
            
            # Match with buy trade
            if buy_trades:
                buy_trade = buy_trades.pop(0)
                
                completed_trades.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'shares': trade['shares'],
                    'pnl': trade['pnl'],
                    'pnl_pct': trade['pnl_pct']
                })
    
    # Calculate statistics
    total_return = (equity / initial_cash - 1) * 100
    
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    avg_profit = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in completed_trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
    
    # Create equity curve
    equity_curve = calculate_equity_curve(trades, initial_cash)
    
    return {
        'final_equity': equity,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'trades': trades,
        'completed_trades': completed_trades,
        'equity_curve': equity_curve
    }
def display_strategy_results(results):
    """
    Display backtesting results in Streamlit
    
    Parameters:
    results (dict): Backtesting results
    """
    # Overall metrics
    st.header("Backtest Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Final Equity", f"${results['final_equity']:.2f}")
        st.metric("Total Return", f"{results['total_return']:.2f}%")
    
    with col2:
        st.metric("Total Trades", results['total_trades'])
        st.metric("Win Rate", f"{results['win_rate']:.2f}%")
    
    with col3:
        st.metric("Winning Trades", results['winning_trades'])
        st.metric("Losing Trades", results['losing_trades'])
    
    with col4:
        st.metric("Avg Profit", f"${results['avg_profit']:.2f}")
        st.metric("Avg Loss", f"${results['avg_loss']:.2f}")
    
    # Equity curve
    st.subheader("Equity Curve")
    
    if isinstance(results['equity_curve'], pd.DataFrame) and not results['equity_curve'].empty:
        fig = px.line(
            results['equity_curve'],
            x='date',
            y='equity',
            labels={'date': 'Date', 'equity': 'Equity ($)'},
            title='Equity Curve'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity curve data available")
    
    # Trades table
    st.subheader("Completed Trades")
    
    if results['completed_trades']:
        # Convert to DataFrame for display
        trades_df = pd.DataFrame(results['completed_trades'])
        
        # Format columns
        trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
        trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
        
        # Calculate holding period
        trades_df['holding_period'] = (trades_df['exit_date'] - trades_df['entry_date']).dt.total_seconds() / 3600  # Hours
        
        # Round numeric columns
        for col in ['entry_price', 'exit_price', 'pnl', 'pnl_pct', 'holding_period']:
            if col in trades_df.columns:
                trades_df[col] = trades_df[col].round(2)
        
        # Display table
        st.dataframe(trades_df)
        
        # Trade distribution
        st.subheader("P&L Distribution")
        
        if 'pnl' in trades_df.columns:
            fig = px.histogram(
                trades_df,
                x='pnl',
                nbins=20,
                labels={'pnl': 'P&L ($)'},
                title='P&L Distribution',
                color_discrete_sequence=['blue']
            )
            
            # Add vertical line at 0
            fig.add_vline(
                x=0,
                line_dash="dash",
                line_color="red"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trades were executed during the backtest period")
    
    # Monthly returns
    if results['completed_trades']:
        st.subheader("Monthly Performance")
        
        # Convert to DataFrame
        trades_df = pd.DataFrame(results['completed_trades'])
        
        # Ensure date columns are datetime
        trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
        
        # Extract month
        trades_df['year_month'] = trades_df['exit_date'].dt.strftime('%Y-%m')
        
        # Group by month
        monthly_pnl = trades_df.groupby('year_month')['pnl'].sum().reset_index()
        
        # Create bar chart
        fig = px.bar(
            monthly_pnl,
            x='year_month',
            y='pnl',
            labels={'year_month': 'Month', 'pnl': 'P&L ($)'},
            title='Monthly P&L',
            color=monthly_pnl['pnl'] > 0,
            color_discrete_map={True: 'green', False: 'red'}
        )
        
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Strategy insights
    st.subheader("Strategy Insights")
    
    # Calculate additional metrics
    if results['total_trades'] > 0:
        profit_factor = abs(results['avg_profit'] * results['winning_trades']) / abs(results['avg_loss'] * results['losing_trades']) if results['losing_trades'] > 0 and results['avg_loss'] != 0 else float('inf')
        
        expectancy = (results['win_rate'] / 100 * results['avg_profit']) + ((1 - results['win_rate'] / 100) * results['avg_loss'])
        
        st.markdown(f"**Profit Factor:** {profit_factor:.2f}")
        st.markdown(f"**Expectancy:** ${expectancy:.2f} per trade")
        
        # Strategy specific insights
        if results['strategy'] == "Moving Average Crossover":
            st.markdown("""
            **Strategy Insights:**
            - Moving average crossovers work best in trending markets
            - Consider using additional filters like volume or volatility
            - Adjust the MA periods based on the stock's characteristics
            """)
        elif results['strategy'] == "RSI Reversal":
            st.markdown("""
            **Strategy Insights:**
            - RSI reversals work best in range-bound markets
            - Consider adjusting overbought/oversold levels based on volatility
            - Add confirmation signals before entering trades
            """)
        elif results['strategy'] == "VWAP Bounce":
            st.markdown("""
            **Strategy Insights:**
            - VWAP bounces work best during normal market conditions
            - Consider the time of day when entering VWAP trades
            - Look for additional confirmation like candlestick patterns
            """)
        elif results['strategy'] == "Breakout":
            st.markdown("""
            **Strategy Insights:**
            - Breakouts perform best with increasing volume
            - Consider using ATR for setting stop loss levels
            - False breakouts are common, so manage risk carefully
            """)
        elif results['strategy'] == "Gap and Go":
            st.markdown("""
            **Strategy Insights:**
            - Gap and Go works best with catalysts like earnings or news
            - Trade in the direction of the gap with momentum
            - Be cautious of fading gaps, especially in strong markets
            """)
    
    # Optimization suggestions
    st.subheader("Optimization Suggestions")
    
    if results['win_rate'] < 40:
        st.markdown("- Consider increasing the filter criteria to improve entry quality")
    
    if results['total_trades'] < 10:
        st.markdown("- Adjust parameters to increase the number of trades for better statistical significance")
    
    if results['avg_profit'] < abs(results['avg_loss']):
        st.markdown("- Optimize take profit and stop loss levels to improve reward-to-risk ratio")
    
    st.markdown("- Try varying the position sizing approach based on volatility or conviction")
    st.markdown("- Consider combining this strategy with complementary strategies for diversification")


def optimize_strategy_parameters(ticker, strategy_type, start_date, end_date, param_grid, risk_params, use_mock_data=False):
    """
    Optimize strategy parameters using grid search
    
    Parameters:
    ticker (str): Stock ticker symbol
    strategy_type (str): Type of strategy to optimize
    start_date (str): Start date for backtesting (YYYY-MM-DD)
    end_date (str): End date for backtesting (YYYY-MM-DD)
    param_grid (dict): Dictionary of parameter grids to search
    risk_params (dict): Risk management parameters
    use_mock_data (bool): If True, use mock data instead of real data
    
    Returns:
    dict: Best parameters and results
    """
    best_result = None
    best_params = None
    best_return = -float('inf')
    
    # Track all results for visualization
    all_results = []
    
    # Generate all parameter combinations
    import itertools
    param_keys = list(param_grid.keys())
    param_values = list(param_grid.values())
    param_combinations = list(itertools.product(*param_values))
    
    total_combinations = len(param_combinations)
    st.info(f"Testing {total_combinations} parameter combinations...")
    
    progress_bar = st.progress(0)
    
    # Test each combination
    for i, combo in enumerate(param_combinations):
        # Update progress
        progress = (i + 1) / total_combinations
        progress_bar.progress(progress)
        
        # Create parameter dictionary
        params = {key: value for key, value in zip(param_keys, combo)}
        
        # Run backtest
        result = backtest_strategy(
            ticker=ticker,
            strategy_type=strategy_type,
            start_date=start_date,
            end_date=end_date,
            strategy_params=params,
            risk_params=risk_params,
            use_mock_data=use_mock_data
        )
        
        # Skip if backtest failed
        if not result:
            continue
        
        # Track result
        result_summary = {
            'params': params,
            'total_return': result['total_return'],
            'win_rate': result['win_rate'],
            'total_trades': result['total_trades'],
            'profit_factor': result['avg_profit'] * result['winning_trades'] / abs(result['avg_loss'] * result['losing_trades']) if result['losing_trades'] > 0 and result['avg_loss'] != 0 else float('inf')
        }
        all_results.append(result_summary)
        
        # Check if this is the best result
        if result['total_return'] > best_return and result['total_trades'] >= 5:
            best_return = result['total_return']
            best_params = params
            best_result = result
    
    # Clear progress bar
    progress_bar.empty()
    
    if best_result:
        return {
            'best_params': best_params,
            'best_result': best_result,
            'all_results': all_results
        }
    else:
        st.error("Optimization failed. No valid results found.")
        return None


def compare_strategies(ticker, start_date, end_date, strategies, risk_params, use_mock_data=False):
    """
    Compare multiple trading strategies on the same stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    start_date (str): Start date for backtesting (YYYY-MM-DD)
    end_date (str): End date for backtesting (YYYY-MM-DD)
    strategies (list): List of strategy dictionaries with 'name' and 'params'
    risk_params (dict): Risk management parameters
    use_mock_data (bool): If True, use mock data instead of real data
    
    Returns:
    dict: Comparison results
    """
    results = {}
    equity_curves = []
    
    for strategy in strategies:
        # Run backtest
        result = backtest_strategy(
            ticker=ticker,
            strategy_type=strategy['name'],
            start_date=start_date,
            end_date=end_date,
            strategy_params=strategy['params'],
            risk_params=risk_params,
            use_mock_data=use_mock_data
        )
        
        if result:
            # Store result
            results[strategy['name']] = result
            
            # Add equity curve for comparison
            equity_curve = result['equity_curve'].copy()
            equity_curve['strategy'] = strategy['name']
            equity_curves.append(equity_curve)
    
    # Combine equity curves
    if equity_curves:
        combined_equity = pd.concat(equity_curves)
    else:
        combined_equity = pd.DataFrame()
    
    return {
        'results': results,
        'combined_equity': combined_equity
    }


def display_strategy_comparison(comparison_results):
    """
    Display strategy comparison results
    
    Parameters:
    comparison_results (dict): Results from compare_strategies function
    """
    if not comparison_results or 'results' not in comparison_results:
        st.error("No comparison results to display")
        return
    
    # Display summary metrics
    st.subheader("Strategy Comparison")
    
    # Create comparison table
    metrics = []
    
    for strategy_name, result in comparison_results['results'].items():
        metrics.append({
            'Strategy': strategy_name,
            'Total Return (%)': round(result['total_return'], 2),
            'Win Rate (%)': round(result['win_rate'], 2),
            'Total Trades': result['total_trades'],
            'Profit Factor': round(
                abs(result['avg_profit'] * result['winning_trades']) / 
                abs(result['avg_loss'] * result['losing_trades']) 
                if result['losing_trades'] > 0 and result['avg_loss'] != 0 else float('inf'), 
                2
            ),
            'Avg. Profit': round(result['avg_profit'], 2),
            'Avg. Loss': round(result['avg_loss'], 2)
        })
    
    # Convert to DataFrame and display
    metrics_df = pd.DataFrame(metrics)
    st.dataframe(metrics_df)
    
    # Display equity curves
    if 'combined_equity' in comparison_results and not comparison_results['combined_equity'].empty:
        st.subheader("Equity Curves Comparison")
        
        fig = px.line(
            comparison_results['combined_equity'],
            x='date',
            y='equity',
            color='strategy',
            labels={'date': 'Date', 'equity': 'Equity ($)'},
            title='Strategy Comparison: Equity Curves'
        )
        
        st.plotly_chart(fig, use_container_width=True)

def display_optimization_results(optimization_results):
    """
    Display optimization results
    
    Parameters:
    optimization_results (dict): Results from optimize_strategy_parameters function
    """
    if not optimization_results:
        st.error("No optimization results to display")
        return
    
    # Display best parameters
    st.subheader("Best Parameters")
    
    # Create parameters table
    params_df = pd.DataFrame({
        'Parameter': optimization_results['best_params'].keys(),
        'Value': optimization_results['best_params'].values()
    })
    
    st.dataframe(params_df)
    
    # Display performance of best parameters
    st.subheader("Performance with Best Parameters")
    
    best_result = optimization_results['best_result']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Return", f"{best_result['total_return']:.2f}%")
    
    with col2:
        st.metric("Win Rate", f"{best_result['win_rate']:.2f}%")
    
    with col3:
        profit_factor = abs(best_result['avg_profit'] * best_result['winning_trades']) / abs(best_result['avg_loss'] * best_result['losing_trades']) if best_result['losing_trades'] > 0 and best_result['avg_loss'] != 0 else float('inf')
        st.metric("Profit Factor", f"{profit_factor:.2f}")
    
    # Display equity curve of best result
    if isinstance(best_result['equity_curve'], pd.DataFrame) and not best_result['equity_curve'].empty:
        fig = px.line(
            best_result['equity_curve'],
            x='date',
            y='equity',
            labels={'date': 'Date', 'equity': 'Equity ($)'},
            title='Equity Curve with Best Parameters'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Display parameter optimization results
    st.subheader("Parameter Optimization Results")
    
    if 'all_results' in optimization_results and optimization_results['all_results']:
        # Convert to DataFrame
        results_df = pd.DataFrame([
            {**r['params'], 'Total Return': r['total_return'], 
             'Win Rate': r['win_rate'], 'Trades': r['total_trades'],
             'Profit Factor': r['profit_factor']}
            for r in optimization_results['all_results']
        ])
        
        # Sort by total return
        results_df = results_df.sort_values('Total Return', ascending=False)
        
        # Display top results
        st.dataframe(results_df.head(10))
        
        # Visualization of parameter impact
        st.subheader

        # Identify most impactful parameters
        param_keys = list(optimization_results['best_params'].keys())
        
        if len(param_keys) >= 1:
            # Create scatter plot for first parameter
            param1 = param_keys[0]
            
            fig = px.scatter(
                results_df,
                x=param1,
                y='Total Return',
                size='Trades',
                color='Win Rate',
                hover_data=['Profit Factor'],
                title=f'Impact of {param1} on Performance',
                color_continuous_scale='RdYlGn'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        if len(param_keys) >= 2:
            # Create scatter plot for second parameter
            param2 = param_keys[1]
            
            fig = px.scatter(
                results_df,
                x=param2,
                y='Total Return',
                size='Trades',
                color='Win Rate',
                hover_data=['Profit Factor'],
                title=f'Impact of {param2} on Performance',
                color_continuous_scale='RdYlGn'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Create 3D scatter plot for both parameters
            fig = px.scatter_3d(
                results_df,
                x=param1,
                y=param2,
                z='Total Return',
                color='Win Rate',
                size='Trades',
                hover_data=['Profit Factor'],
                title=f'Combined Impact of {param1} and {param2}',
                color_continuous_scale='RdYlGn'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No parameter impact data available")
    
    # Recommendations
    st.subheader("Recommendations")
    
    st.markdown("""
    Based on the optimization results, consider the following:
    
    1. **Test Robustness**: Test the best parameters on different time periods to ensure they're robust
    2. **Consider Trade-offs**: Higher returns might come with higher risk or fewer trades
    3. **Look for Patterns**: Check if certain parameter values consistently perform better
    4. **Combine Strategies**: Consider combining strategies for better overall performance
    """)



