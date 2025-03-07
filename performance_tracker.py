#performance_tracker.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

def log_trade(trade, balance_after=None):
    """
    Log a trade for performance tracking
    
    Parameters:
    trade (dict): Trade information
    balance_after (float): Account balance after the trade
    """
    # In a production app, this would log to a database
    # For this demo, we'll just use session state
    if 'trade_log' not in st.session_state:
        st.session_state.trade_log = []
    
    # Add trade to log with timestamp
    log_entry = trade.copy()
    log_entry['log_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry['balance_after'] = balance_after
    
    st.session_state.trade_log.append(log_entry)
    
    return True

def calculate_performance_metrics(trade_history):
    """
    Calculate performance metrics based on trade history
    
    Parameters:
    trade_history (list): List of historical trades
    
    Returns:
    dict: Dictionary of performance metrics
    """
    # Filter closed trades
    closed_trades = [t for t in trade_history if 'status' in t and t['status'] == 'closed']
    
    if not closed_trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'avg_holding_time': 0,
            'net_pnl': 0
        }
    
    # Calculate win/loss statistics
    winning_trades = [t for t in closed_trades if 'pnl' in t and t['pnl'] > 0]
    losing_trades = [t for t in closed_trades if 'pnl' in t and t['pnl'] <= 0]
    
    win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
    
    # Calculate profit metrics
    total_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
    total_loss = sum(t['pnl'] for t in losing_trades) if losing_trades else 0
    net_pnl = total_profit + total_loss
    
    profit_factor = abs(total_profit / total_loss) if total_loss < 0 else 0
    
    # Calculate average trade metrics
    avg_win = total_profit / len(winning_trades) if winning_trades else 0
    avg_loss = total_loss / len(losing_trades) if losing_trades else 0
    
    # Find largest win/loss
    largest_win = max([t['pnl'] for t in winning_trades]) if winning_trades else 0
    largest_loss = min([t['pnl'] for t in losing_trades]) if losing_trades else 0
    
    # Calculate average holding time
    holding_times = []
    for trade in closed_trades:
        if 'date_opened' in trade and 'date_closed' in trade:
            try:
                open_time = datetime.strptime(trade['date_opened'], '%Y-%m-%d %H:%M:%S')
                close_time = datetime.strptime(trade['date_closed'], '%Y-%m-%d %H:%M:%S')
                holding_time = (close_time - open_time).total_seconds() / 3600  # Hours
                holding_times.append(holding_time)
            except:
                pass
    
    avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
    
    # Calculate drawdown
    if 'balance_after' in closed_trades[0]:
        balances = [t['balance_after'] for t in closed_trades if 'balance_after' in t]
        max_balance = max(balances)
        current_balance = balances[-1]
        max_drawdown = ((max_balance - min(balances)) / max_balance) * 100
    else:
        max_drawdown = 0
    
    return {
        'total_trades': len(closed_trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'avg_holding_time': avg_holding_time,
        'net_pnl': net_pnl,
        'max_drawdown': max_drawdown
    }

def calculate_daily_performance(trade_history):
    """
    Calculate daily performance based on trade history
    
    Parameters:
    trade_history (list): List of historical trades
    
    Returns:
    DataFrame: DataFrame with daily performance metrics
    """
    # Filter closed trades
    closed_trades = [t for t in trade_history if 'status' in t and t['status'] == 'closed']
    
    if not closed_trades:
        return pd.DataFrame()
    
    # Group trades by day
    daily_performance = {}
    
    for trade in closed_trades:
        if 'date_closed' in trade:
            try:
                close_date = datetime.strptime(trade['date_closed'], '%Y-%m-%d %H:%M:%S').date()
                close_date_str = close_date.strftime('%Y-%m-%d')
                
                if close_date_str not in daily_performance:
                    daily_performance[close_date_str] = {
                        'date': close_date_str,
                        'pnl': 0,
                        'trades': 0,
                        'wins': 0,
                        'losses': 0
                    }
                
                # Update daily stats
                daily_performance[close_date_str]['pnl'] += trade.get('pnl', 0)
                daily_performance[close_date_str]['trades'] += 1
                
                if trade.get('pnl', 0) > 0:
                    daily_performance[close_date_str]['wins'] += 1
                else:
                    daily_performance[close_date_str]['losses'] += 1
            except:
                pass
    
    # Convert to DataFrame
    if daily_performance:
        df = pd.DataFrame(list(daily_performance.values()))
        df['win_rate'] = df['wins'] / df['trades'] * 100
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate cumulative P&L
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        return df
    
    return pd.DataFrame()

def display_performance_metrics(trade_history):
    """
    Display performance metrics in Streamlit
    
    Parameters:
    trade_history (list): List of historical trades
    """
    # Calculate metrics
    metrics = calculate_performance_metrics(trade_history)
    
    # Display metrics in columns
    st.header("Trading Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", metrics['total_trades'])
        st.metric("Win Rate", f"{metrics['win_rate']:.2f}%")
    
    with col2:
        st.metric("Net P&L", f"${metrics['net_pnl']:.2f}")
        st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
    
    with col3:
        st.metric("Average Win", f"${metrics['avg_win']:.2f}")
        st.metric("Average Loss", f"${metrics['avg_loss']:.2f}")
    
    with col4:
        st.metric("Largest Win", f"${metrics['largest_win']:.2f}")
        st.metric("Largest Loss", f"${metrics['largest_loss']:.2f}")
    
    # Calculate daily performance
    daily_performance = calculate_daily_performance(trade_history)
    
    if not daily_performance.empty:
        # Display daily performance chart
        st.subheader("Daily P&L")
        
        fig = px.bar(
            daily_performance,
            x='date',
            y='pnl',
            color=daily_performance['pnl'] > 0,
            color_discrete_map={True: 'green', False: 'red'},
            labels={'date': 'Date', 'pnl': 'P&L ($)', 'color': 'Profitable'},
            title='Daily Profit/Loss'
        )
        
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Display cumulative P&L
        st.subheader("Cumulative P&L")
        
        fig = px.line(
            daily_performance,
            x='date',
            y='cumulative_pnl',
            labels={'date': 'Date', 'cumulative_pnl': 'Cumulative P&L ($)'},
            title='Cumulative Profit/Loss'
        )
        
        # Add annotations for key points
        max_pnl = daily_performance['cumulative_pnl'].max()
        max_date = daily_performance.loc[daily_performance['cumulative_pnl'].idxmax(), 'date']
        
        min_pnl = daily_performance['cumulative_pnl'].min()
        min_date = daily_performance.loc[daily_performance['cumulative_pnl'].idxmin(), 'date']
        
        current_pnl = daily_performance['cumulative_pnl'].iloc[-1]
        
        # Add annotations
        fig.add_annotation(
            x=max_date,
            y=max_pnl,
            text=f"High: ${max_pnl:.2f}",
            showarrow=True,
            arrowhead=1
        )
        
        if min_pnl < 0:
            fig.add_annotation(
                x=min_date,
                y=min_pnl,
                text=f"Low: ${min_pnl:.2f}",
                showarrow=True,
                arrowhead=1
            )
        
        fig.add_annotation(
            x=daily_performance['date'].iloc[-1],
            y=current_pnl,
            text=f"Current: ${current_pnl:.2f}",
            showarrow=True,
            arrowhead=1
        )
        
        fig.update_layout(
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray',
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='Black'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Win rate by day of week
        daily_performance['day_of_week'] = daily_performance['date'].dt.day_name()
        
        # Group by day of week
        day_performance = daily_performance.groupby('day_of_week').agg({
            'pnl': 'sum',
            'trades': 'sum',
            'wins': 'sum'
        }).reset_index()
        
        # Calculate win rate
        day_performance['win_rate'] = day_performance['wins'] / day_performance['trades'] * 100
        
        # Sort by days of week
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        day_performance['day_of_week'] = pd.Categorical(
            day_performance['day_of_week'], 
            categories=days_order, 
            ordered=True
        )
        day_performance = day_performance.sort_values('day_of_week')
        
        # Display day of week analysis
        st.subheader("Performance by Day of Week")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Win rate by day of week
            fig = px.bar(
                day_performance,
                x='day_of_week',
                y='win_rate',
                labels={'day_of_week': 'Day', 'win_rate': 'Win Rate (%)'},
                title='Win Rate by Day of Week',
                color='win_rate',
                color_continuous_scale='RdYlGn'
            )
            
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # P&L by day of week
            fig = px.bar(
                day_performance,
                x='day_of_week',
                y='pnl',
                labels={'day_of_week': 'Day', 'pnl': 'P&L ($)'},
                title='P&L by Day of Week',
                color=day_performance['pnl'] > 0,
                color_discrete_map={True: 'green', False: 'red'}
            )
            
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("Complete some trades to see detailed performance metrics")
    
    # Display trading strengths and weaknesses
    if metrics['total_trades'] > 5:
        st.subheader("Trading Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Strengths")
            
            strengths = []
            
            if metrics['win_rate'] > 60:
                strengths.append("✅ High win rate above 60%")
            
            if metrics['profit_factor'] > 2:
                strengths.append("✅ Strong profit factor above 2.0")
            
            if metrics['avg_win'] > abs(metrics['avg_loss']) * 1.5:
                strengths.append("✅ Good reward-to-risk ratio")
            
            if metrics['avg_holding_time'] < 2:  # Less than 2 hours
                strengths.append("✅ Quick decision making with short hold times")
            
            if not strengths:
                strengths.append("Not enough data to determine strengths")
            
            for strength in strengths:
                st.markdown(strength)
        
        with col2:
            st.markdown("### Areas for Improvement")
            
            weaknesses = []
            
            if metrics['win_rate'] < 40:
                weaknesses.append("🔸 Low win rate below 40%")
            
            if 0 < metrics['profit_factor'] < 1.5:
                weaknesses.append("🔸 Profit factor below 1.5")
            
            if metrics['avg_win'] < abs(metrics['avg_loss']):
                weaknesses.append("🔸 Average loss exceeds average win")
            
            if metrics['max_drawdown'] > 20:
                weaknesses.append(f"🔸 High maximum drawdown of {metrics['max_drawdown']:.2f}%")
            
            if not weaknesses:
                weaknesses.append("Not enough data to determine areas for improvement")
            
            for weakness in weaknesses:
                st.markdown(weakness)
        
        # Recommendations
        st.subheader("Recommendations")
        
        recommendations = []
        
        if metrics['win_rate'] < 40:
            recommendations.append("Improve entry criteria to increase win rate")
        
        if metrics['avg_win'] < abs(metrics['avg_loss']):
            recommendations.append("Set wider profit targets or tighter stop losses to improve reward-to-risk ratio")
        
        if metrics['max_drawdown'] > 20:
            recommendations.append("Reduce position size to limit drawdowns")
        
        if metrics['profit_factor'] < 1.5:
            recommendations.append("Focus on increasing win rate or improving reward-to-risk ratio")
        
        if not recommendations:
            recommendations.append("Keep trading consistently with your current approach")
        
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")
    
    # Help section
    with st.expander("📚 Understanding Performance Metrics"):
        st.markdown("""
        ## Key Performance Metrics Explained
        
        ### Win Rate
        The percentage of trades that are profitable. A win rate above 50% is generally considered good for day trading.
        
        ### Profit Factor
        Total profit divided by total loss. A profit factor above 1.5 is good, while above 2.0 is excellent.
        
        ### Average Win vs. Average Loss
        Ideally, your average win should be larger than your average loss. A ratio of 1.5:1 or higher is desirable.
        
        ### Maximum Drawdown
        The largest peak-to-trough decline in your account balance. Lower drawdowns indicate better risk management.
        
        ### Daily P&L
        Shows your profit or loss for each trading day. Look for consistency rather than occasional big wins.
        
        ### Performance by Day of Week
        Helps identify which days you trade best or worst. You might consider trading more on your strongest days.
        
        ### Recommendations
        Personalized suggestions based on your trading performance metrics to help improve your results.
        """)