#paper_trading.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import uuid

from stock_data import fetch_stock_data

class PaperTradingSimulator:
    """
    A simulator for paper trading stocks for day trading practice
    """
    
    def __init__(self, initial_balance=100000.0, trades=None, trade_history=None):
        """
        Initialize the paper trading simulator
        
        Parameters:
        initial_balance (float): Initial account balance in USD
        trades (list): List of existing trades (optional)
        trade_history (list): List of historical trades (optional)
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = trades if trades is not None else []
        self.trade_history = trade_history if trade_history is not None else []
    
    def place_trade(self, symbol, trade_type, quantity, price, stop_loss=None, take_profit=None):
        """
        Place a trade (buy or sell short)
        
        Parameters:
        symbol (str): Stock ticker symbol
        trade_type (str): 'buy' or 'sell_short'
        quantity (int): Number of shares
        price (float): Price per share
        stop_loss (float): Stop loss price (optional)
        take_profit (float): Take profit price (optional)
        
        Returns:
        dict: Result of the trade operation
        """
        # Calculate trade value
        trade_value = price * quantity
        
        # Check if enough balance for the trade
        if trade_value > self.balance:
            return {
                'success': False,
                'message': f"Insufficient funds. Required: ${trade_value:.2f}, Available: ${self.balance:.2f}"
            }
        
        # Validate stop loss and take profit
        if trade_type == 'buy':
            if stop_loss and stop_loss >= price:
                return {
                    'success': False,
                    'message': "Stop loss must be below the entry price for long positions"
                }
            if take_profit and take_profit <= price:
                return {
                    'success': False,
                    'message': "Take profit must be above the entry price for long positions"
                }
        elif trade_type == 'sell_short':
            if stop_loss and stop_loss <= price:
                return {
                    'success': False,
                    'message': "Stop loss must be above the entry price for short positions"
                }
            if take_profit and take_profit >= price:
                return {
                    'success': False,
                    'message': "Take profit must be below the entry price for short positions"
                }
        
        # Add trade to list
        trade_id = str(uuid.uuid4())
        trade = {
            'id': trade_id,
            'symbol': symbol,
            'trade_type': trade_type,
            'quantity': quantity,
            'price': price,
            'value': trade_value,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'date_opened': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'open'
        }
        
        self.trades.append(trade)
        
        # Deduct from balance
        self.balance -= trade_value
        
        # Add to trade history
        trade_history_entry = trade.copy()
        self.trade_history.append(trade_history_entry)
        
        return {
            'success': True,
            'message': f"Successfully placed {'long' if trade_type == 'buy' else 'short'} order for {quantity} shares of {symbol} at ${price:.2f}"
        }
    
    def close_position(self, position_idx=None, trade_id=None, price=None):
        """
        Close an open position
        
        Parameters:
        position_idx (int): Index of the trade in the trades list (optional)
        trade_id (str): ID of the trade to close (optional)
        price (float): Closing price (if None, current market price will be used)
        
        Returns:
        dict: Result of the close operation
        """
        # Find the trade
        trade = None
        if position_idx is not None and position_idx < len(self.trades):
            trade = self.trades[position_idx]
        elif trade_id is not None:
            for t in self.trades:
                if t['id'] == trade_id:
                    trade = t
                    break
        
        if not trade:
            return {
                'success': False,
                'message': "Trade not found"
            }
        
        # Check if the position is already closed
        if trade['status'] != 'open':
            return {
                'success': False,
                'message': f"Position {trade['symbol']} is already closed"
            }
        
        # Get closing price if not provided
        if price is None:
            try:
                stock_data = fetch_stock_data(trade['symbol'], period="1d")
                price = stock_data['Close'].iloc[-1]
            except Exception as e:
                return {
                    'success': False,
                    'message': f"Error fetching current price for {trade['symbol']}: {str(e)}"
                }
        
        # Calculate P&L
        if trade['trade_type'] == 'buy':
            pnl = (price - trade['price']) * trade['quantity']
        else:  # sell_short
            pnl = (trade['price'] - price) * trade['quantity']
        
        # Update trade information
        trade['status'] = 'closed'
        trade['date_closed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade['exit_price'] = price
        trade['pnl'] = pnl
        
        # Update balance
        closing_value = price * trade['quantity']
        self.balance += closing_value + pnl if trade['trade_type'] == 'buy' else closing_value
        
        # Update the trade in the list
        if position_idx is not None:
            self.trades[position_idx] = trade
        else:
            for i, t in enumerate(self.trades):
                if t['id'] == trade_id:
                    self.trades[i] = trade
                    break
        
        # Update trade history
        for i, t in enumerate(self.trade_history):
            if t['id'] == trade['id']:
                self.trade_history[i] = trade
                break
        
        return {
            'success': True,
            'message': f"Closed {trade['symbol']} position with {'profit' if pnl >= 0 else 'loss'} of ${pnl:.2f}"
        }
    
    def get_position_index(self, trade):
        """
        Get the index of a trade in the trades list
        
        Parameters:
        trade (dict): The trade to find
        
        Returns:
        int: Index of the trade in the trades list
        """
        for i, t in enumerate(self.trades):
            if t.get('id') == trade.get('id'):
                return i
        return -1
    
    def check_stop_loss_take_profit(self):
        """
        Check all open positions for stop loss and take profit triggers
        
        Returns:
        list: List of trades that were closed
        """
        closed_trades = []
        
        for i, trade in enumerate(self.trades):
            if trade['status'] == 'open' and (trade.get('stop_loss') or trade.get('take_profit')):
                try:
                    # Get current price
                    stock_data = fetch_stock_data(trade['symbol'], period="1d")
                    current_price = stock_data['Close'].iloc[-1]
                    
                    # Check stop loss
                    stop_triggered = False
                    if trade.get('stop_loss'):
                        if (trade['trade_type'] == 'buy' and current_price <= trade['stop_loss']) or \
                           (trade['trade_type'] == 'sell_short' and current_price >= trade['stop_loss']):
                            stop_triggered = True
                    
                    # Check take profit
                    profit_triggered = False
                    if trade.get('take_profit'):
                        if (trade['trade_type'] == 'buy' and current_price >= trade['take_profit']) or \
                           (trade['trade_type'] == 'sell_short' and current_price <= trade['take_profit']):
                            profit_triggered = True
                    
                    # Close position if triggered
                    if stop_triggered or profit_triggered:
                        result = self.close_position(position_idx=i, price=current_price)
                        if result['success']:
                            closed_trades.append({
                                'trade': trade,
                                'reason': 'stop_loss' if stop_triggered else 'take_profit',
                                'price': current_price
                            })
                except Exception as e:
                    st.warning(f"Error checking stop/take profit for {trade['symbol']}: {str(e)}")
        
        return closed_trades
    
    def get_portfolio_summary(self):
        """
        Get a summary of the portfolio
        
        Returns:
        dict: Portfolio summary information
        """
        # Calculate portfolio statistics
        total_open_positions = len([t for t in self.trades if t['status'] == 'open'])
        total_watchlist = len([t for t in self.trades if t['status'] == 'watchlist'])
        
        # Calculate unrealized P&L
        unrealized_pnl = 0
        position_value = 0
        
        for trade in self.trades:
            if trade['status'] == 'open':
                try:
                    # Get current price
                    stock_data = fetch_stock_data(trade['symbol'], period="1d")
                    current_price = stock_data['Close'].iloc[-1]
                    
                    # Calculate trade P&L
                    if trade['trade_type'] == 'buy':
                        trade_pnl = (current_price - trade['price']) * trade['quantity']
                    else:  # sell_short
                        trade_pnl = (trade['price'] - current_price) * trade['quantity']
                    
                    unrealized_pnl += trade_pnl
                    position_value += current_price * trade['quantity']
                except:
                    # Use original price if can't get current price
                    position_value += trade['price'] * trade['quantity']
        
        # Calculate realized P&L
        realized_pnl = sum([t.get('pnl', 0) for t in self.trade_history if t['status'] == 'closed'])
        
        # Calculate win rate
        closed_trades = [t for t in self.trade_history if t['status'] == 'closed']
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        return {
            'balance': self.balance,
            'initial_balance': self.initial_balance,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'return_pct': (unrealized_pnl + realized_pnl) / self.initial_balance * 100,
            'open_positions': total_open_positions,
            'watchlist_items': total_watchlist,
            'position_value': position_value,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'win_rate': win_rate
        }
    
    def add_to_watchlist(self, symbol, price):
        """
        Add a stock to the watchlist
        
        Parameters:
        symbol (str): Stock ticker symbol
        price (float): Current price
        
        Returns:
        bool: True if successful, False otherwise
        """
        # Check if already in watchlist
        for trade in self.trades:
            if trade['symbol'] == symbol and trade['status'] == 'watchlist':
                return False
        
        # Add to watchlist
        trade_id = str(uuid.uuid4())
        self.trades.append({
            'id': trade_id,
            'symbol': symbol,
            'price': price,
            'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'watchlist'
        })
        
        return True
    
    def remove_from_watchlist(self, symbol=None, trade_id=None):
        """
        Remove a stock from the watchlist
        
        Parameters:
        symbol (str): Stock ticker symbol (optional)
        trade_id (str): Trade ID (optional)
        
        Returns:
        bool: True if successful, False otherwise
        """
        # Find the trade
        for i, trade in enumerate(self.trades):
            if trade['status'] == 'watchlist':
                if (symbol and trade['symbol'] == symbol) or (trade_id and trade['id'] == trade_id):
                    del self.trades[i]
                    return True
        
        return False