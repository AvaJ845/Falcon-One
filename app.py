# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json
import os

# Import custom modules
from stock_data import fetch_stock_data, get_stock_info, calculate_historical_volatility
from day_trading_scanner import scan_for_day_trading_opportunities, get_weekly_picks
from technical_analysis import analyze_stock, get_support_resistance, calculate_technical_indicators
from paper_trading import PaperTradingSimulator
from dashboard import create_dashboard
from performance_tracker import display_performance_metrics, log_trade
from strategy_analyzer import backtest_strategy, display_strategy_results
from market_sentiment import get_market_sentiment, analyze_news_sentiment

# Set page configuration
st.set_page_config(
    page_title="FalconOne - Intraday Scanner",
    page_icon="🪿",
    layout="wide"
)

# App title and branding
st.markdown("""
<div style='text-align: center;'>
    <h1>🪿 FalconOne v1</h1>
    <p><i>Day Trading Pro</i></p>
    <p>AvaResearch LLC</p>
</div>
""", unsafe_allow_html=True)

st.title("FalconOne - Intraday Scanner")
st.markdown("""
This application helps you identify day trading opportunities, analyze technical indicators, 
and simulate trades with paper money. It also provides weekly stock picks with estimated gain potential.
""")

# Define session state for data persistence
if 'data_initialized' not in st.session_state:
    st.session_state.data_initialized = False

# Initialize session state for paper trading
if 'paper_trades' not in st.session_state:
    st.session_state.paper_trades = []
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 100000.0  # Default starting balance
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'weekly_picks' not in st.session_state:
    st.session_state.weekly_picks = None
if 'weekly_picks_date' not in st.session_state:
    st.session_state.weekly_picks_date = None

# Load saved data if exists
def load_saved_data():
    try:
        if os.path.exists('day_trader_data.json'):
            with open('day_trader_data.json', 'r') as f:
                data = json.load(f)
                
                # Check if data is less than a month old
                if 'save_date' in data:
                    save_date = datetime.strptime(data['save_date'], '%Y-%m-%d')
                    if (datetime.now() - save_date).days <= 30:
                        st.session_state.paper_trades = data.get('paper_trades', [])
                        st.session_state.account_balance = data.get('account_balance', 100000.0)
                        st.session_state.trade_history = data.get('trade_history', [])
                        st.session_state.weekly_picks = data.get('weekly_picks', None)
                        st.session_state.weekly_picks_date = data.get('weekly_picks_date', None)
                        
            st.session_state.data_initialized = True
            return True
    except Exception as e:
        st.warning(f"Could not load saved data: {str(e)}")
    return False

# Save current data
def save_current_data():
    try:
        data = {
            'save_date': datetime.now().strftime('%Y-%m-%d'),
            'paper_trades': st.session_state.paper_trades,
            'account_balance': st.session_state.account_balance,
            'trade_history': st.session_state.trade_history,
            'weekly_picks': st.session_state.weekly_picks,
            'weekly_picks_date': st.session_state.weekly_picks_date
        }
        
        with open('day_trader_data.json', 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        st.warning(f"Could not save data: {str(e)}")
    return False

# Try to load saved data on app startup
if not st.session_state.data_initialized:
    load_saved_data()

# Sidebar for navigation and controls
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a page:", [
    "Dashboard", 
    "Day Trading Scanner", 
    "Technical Analysis", 
    "Strategy Backtester",
    "Paper Trading",
    "Performance Analytics"
])

# Check if weekly picks need to be updated (once per week)
def update_weekly_picks():
    current_date = datetime.now().date()
    
    # If we don't have weekly picks or they're more than 7 days old
    if (st.session_state.weekly_picks_date is None or 
        (current_date - datetime.strptime(st.session_state.weekly_picks_date, '%Y-%m-%d').date()).days >= 7):
        with st.spinner("Generating weekly picks..."):
            weekly_picks = get_weekly_picks()
            if not weekly_picks.empty:
                st.session_state.weekly_picks = weekly_picks.to_dict('records')
                st.session_state.weekly_picks_date = current_date.strftime('%Y-%m-%d')
                # Save the updated data
                save_current_data()

# Update weekly picks if needed
update_weekly_picks()

# Dashboard page
if page == "Dashboard":
    create_dashboard()

# Day Trading Scanner page
elif page == "Day Trading Scanner":
    st.header("Day Trading Opportunity Scanner")
    
    scanner_type = st.radio(
        "Scanner Type",
        ["Gap Scanner", "Momentum Scanner", "Volatility Scanner", "Reversal Scanner"],
        horizontal=True
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_price = st.number_input("Min Price ($)", min_value=1.0, max_value=100.0, value=5.0)
    
    with col2:
        max_price = st.number_input("Max Price ($)", min_value=10.0, max_value=1000.0, value=200.0)
    
    with col3:
        min_volume = st.number_input("Min Volume", min_value=100000, max_value=10000000, value=500000, step=100000)
    
    scan_button = st.button("Scan for Opportunities")
    
    if scan_button:
        with st.spinner("Scanning for day trading opportunities..."):
            opportunities = scan_for_day_trading_opportunities(
                scanner_type=scanner_type,
                min_price=min_price,
                max_price=max_price,
                min_volume=min_volume
            )
            
            if not opportunities.empty:
                st.subheader(f"{scanner_type} Results")
                st.dataframe(opportunities)
                
                # Display top opportunities
                st.subheader("Top Trading Opportunities")
                
                # Display top 3 stocks
                for i, (_, row) in enumerate(opportunities.head(3).iterrows()):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.subheader(f"{i+1}. {row['Symbol']} - {row['Company']}")
                        st.metric("Current Price", f"${row['Price']:.2f}", f"{row['Change']}%")
                        st.metric("Volume", f"{row['Volume']:,}", f"{row['Volume % Change']}% vs Avg")
                        
                        # Add to paper trading button
                        if st.button(f"Add {row['Symbol']} to Paper Trading", key=f"add_{row['Symbol']}"):
                            st.session_state.paper_trades.append({
                                'symbol': row['Symbol'],
                                'price': row['Price'],
                                'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'status': 'watchlist'
                            })
                            save_current_data()
                            st.success(f"Added {row['Symbol']} to watchlist")
                    
                    with col2:
                        # Show mini chart
                        try:
                            stock_data = fetch_stock_data(row['Symbol'], period="5d", interval="15m")
                            fig = px.line(
                                stock_data, 
                                x=stock_data.index, 
                                y="Close",
                                title=f"{row['Symbol']} - Last 5 Days (15-min intervals)"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        except:
                            st.info(f"Could not load chart for {row['Symbol']}")
            else:
                st.info("No opportunities found matching your criteria. Try adjusting your filters.")
    
    # Weekly Picks Section
    st.header("Weekly Day Trading Picks")
    
    if st.session_state.weekly_picks:
        weekly_picks_df = pd.DataFrame(st.session_state.weekly_picks)
        
        st.subheader(f"Top Picks for Week of {st.session_state.weekly_picks_date}")
        st.info("These picks are updated weekly and represent stocks with high day trading potential based on technical analysis and market conditions.")
        
        # Display picks in a nice format
        for i, row in enumerate(st.session_state.weekly_picks[:5]):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.subheader(f"{i+1}. {row['symbol']} - {row['name']}")
                st.write(f"**Sector:** {row['sector']}")
                st.write(f"**Strategy:** {row['strategy']}")
            
            with col2:
                st.metric("Price", f"${row['price']:.2f}")
                st.metric("Estimated Gain", f"{row['estimated_gain']}%")
            
            with col3:
                st.metric("Risk Level", row['risk_level'])
                
                # Add to watchlist button
                if st.button(f"Add to Watchlist", key=f"watch_{row['symbol']}"):
                    # Check if already in watchlist
                    exists = False
                    for trade in st.session_state.paper_trades:
                        if trade['symbol'] == row['symbol'] and trade['status'] == 'watchlist':
                            exists = True
                            break
                    
                    if not exists:
                        st.session_state.paper_trades.append({
                            'symbol': row['symbol'],
                            'price': row['price'],
                            'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'watchlist'
                        })
                        save_current_data()
                        st.success(f"Added {row['symbol']} to watchlist")
                    else:
                        st.info(f"{row['symbol']} is already in your watchlist")
    else:
        st.info("Weekly picks are being generated. Please check back later.")

# Technical Analysis page
elif page == "Technical Analysis":
    st.header("Technical Analysis for Day Trading")
    
    # Stock input
    stock_input = st.text_input("Enter Stock Symbol", "AAPL").upper()
    
    time_frame = st.radio(
        "Select Time Frame",
        ["1d", "5d", "1mo", "3mo"],
        horizontal=True,
        index=0
    )
    
    interval_options = {
        "1d": ["1m", "2m", "5m", "15m", "30m", "1h"],
        "5d": ["5m", "15m", "30m", "1h"],
        "1mo": ["30m", "1h", "1d"],
        "3mo": ["1d", "5d"]
    }
    
    interval = st.selectbox(
        "Select Interval",
        interval_options[time_frame],
        index=min(3, len(interval_options[time_frame])-1)
    )
    
    analyze_button = st.button("Analyze Stock")
    
    if analyze_button and stock_input:
        with st.spinner(f"Analyzing {stock_input}..."):
            # Get stock information
            stock_info = get_stock_info(stock_input)
            
            if stock_info:
                # Analyze the stock
                analysis_results, stock_data = analyze_stock(
                    stock_input, 
                    period=time_frame, 
                    interval=interval
                )
                
                if not stock_data.empty:
                    # Display stock information
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Current Price", f"${analysis_results['current_price']:.2f}", 
                                  f"{analysis_results['price_change']:.2f}%")
                    
                    with col2:
                        st.metric("Volume", f"{analysis_results['volume']:,}", 
                                  f"{analysis_results['volume_change']:.2f}% vs Avg")
                    
                    with col3:
                        st.metric("Volatility", f"{analysis_results['volatility']:.2f}%")
                    
                    # Display chart with indicators
                    st.subheader(f"{stock_input} Price Chart with Indicators")
                    
                    # Create indicator selection
                    indicators = st.multiselect(
                        "Select Technical Indicators",
                        ["SMA20", "SMA50", "SMA200", "EMA9", "RSI", "MACD", "Bollinger Bands", "Support/Resistance"],
                        default=["SMA20", "SMA50", "Bollinger Bands"]
                    )
                    
                    # Calculate indicators
                    indicator_data = calculate_technical_indicators(stock_data, indicators)
                    
                    # Create figure
                    fig = go.Figure()
                    
                    # Add candlestick chart
                    fig.add_trace(go.Candlestick(
                        x=stock_data.index,
                        open=stock_data['Open'],
                        high=stock_data['High'],
                        low=stock_data['Low'],
                        close=stock_data['Close'],
                        name="Price"
                    ))
                    
                    # Add selected indicators
                    for indicator, values in indicator_data.items():
                        if isinstance(values, pd.Series):
                            fig.add_trace(go.Scatter(
                                x=values.index,
                                y=values,
                                mode='lines',
                                name=indicator
                            ))
                        elif isinstance(values, dict):  # For indicators with multiple lines (e.g., Bollinger Bands)
                            for name, series in values.items():
                                fig.add_trace(go.Scatter(
                                    x=series.index,
                                    y=series,
                                    mode='lines',
                                    name=f"{indicator} {name}"
                                ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{stock_input} - {analysis_results['name']}",
                        xaxis_title="Date",
                        yaxis_title="Price",
                        height=600,
                        xaxis_rangeslider_visible=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display technical analysis
                    st.subheader("Technical Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Signal Summary")
                        for signal, value in analysis_results['signals'].items():
                            if value == 'Buy':
                                st.markdown(f"**{signal}:** 🟢 {value}")
                            elif value == 'Sell':
                                st.markdown(f"**{signal}:** 🔴 {value}")
                            else:
                                st.markdown(f"**{signal}:** ⚪ {value}")
                    
                    with col2:
                        st.subheader("Overall Recommendation")
                        recommendation = analysis_results['recommendation']
                        if recommendation == 'Strong Buy':
                            st.markdown("### 🟢 Strong Buy")
                        elif recommendation == 'Buy':
                            st.markdown("### 🟢 Buy")
                        elif recommendation == 'Neutral':
                            st.markdown("### ⚪ Neutral")
                        elif recommendation == 'Sell':
                            st.markdown("### 🔴 Sell")
                        else:
                            st.markdown("### 🔴 Strong Sell")
                    
                    # Display support and resistance levels
                    if "Support/Resistance" in indicators:
                        st.subheader("Support and Resistance Levels")
                        
                        support_resistance = get_support_resistance(stock_data)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Support Levels")
                            for level in support_resistance['support']:
                                st.write(f"${level:.2f}")
                        
                        with col2:
                            st.subheader("Resistance Levels")
                            for level in support_resistance['resistance']:
                                st.write(f"${level:.2f}")
                    
                    # Day Trading Analysis
                    st.subheader("Day Trading Strategy Analysis")
                    
                    # Get day trading specific metrics
                    day_trading_analysis = analysis_results['day_trading']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Avg. Daily Range", f"${day_trading_analysis['avg_daily_range']:.2f}")
                        st.metric("Avg. Intraday Volatility", f"{day_trading_analysis['intraday_volatility']:.2f}%")
                    
                    with col2:
                        st.metric("Best Entry Time", day_trading_analysis['best_entry_time'])
                        st.metric("Liquidity Score", f"{day_trading_analysis['liquidity_score']}/10")
                    
                    with col3:
                        st.metric("Recommended Stop Loss", f"${day_trading_analysis['stop_loss']:.2f}")
                        st.metric("Profit Target", f"${day_trading_analysis['profit_target']:.2f}")
                    
                    # Add to paper trading button
                    if st.button(f"Add {stock_input} to Paper Trading"):
                        # Add to watchlist
                        st.session_state.paper_trades.append({
                            'symbol': stock_input,
                            'price': analysis_results['current_price'],
                            'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'watchlist',
                            'stop_loss': day_trading_analysis['stop_loss'],
                            'profit_target': day_trading_analysis['profit_target']
                        })
                        save_current_data()
                        st.success(f"Added {stock_input} to paper trading watchlist")
                    
                    # Market Sentiment Analysis
                    st.subheader("Market Sentiment Analysis")
                    
                    try:
                        sentiment_data = get_market_sentiment(stock_input)
                        news_sentiment = analyze_news_sentiment(stock_input)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Overall Sentiment", sentiment_data['overall'])
                        
                        with col2:
                            st.metric("Social Media Sentiment", sentiment_data['social_score'])
                        
                        with col3:
                            st.metric("News Sentiment", news_sentiment['score'])
                        
                        # Display news headlines
                        st.subheader("Recent News Headlines")
                        
                        for headline in news_sentiment['headlines'][:5]:
                            sentiment_color = "green" if headline['sentiment'] > 0 else "red" if headline['sentiment'] < 0 else "gray"
                            st.markdown(f"<div style='padding: 10px; border-left: 5px solid {sentiment_color};'>"
                                        f"<p>{headline['title']}</p>"
                                        f"<p style='color: {sentiment_color};'>{headline['source']} - {headline['date']}</p>"
                                        f"</div>", unsafe_allow_html=True)
                    except:
                        st.info("Sentiment analysis not available for this stock")
                else:
                    st.error(f"Could not fetch data for {stock_input}. Please check the symbol and try again.")
            else:
                st.error(f"Could not find stock information for {stock_input}. Please check the symbol and try again.")

# Strategy Backtester page
elif page == "Strategy Backtester":
    st.header("Day Trading Strategy Backtester")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_input = st.text_input("Enter Stock Symbol for Backtesting", "AAPL").upper()
    
    with col2:
        strategy_type = st.selectbox(
            "Select Strategy",
            ["Moving Average Crossover", "RSI Reversal", "VWAP Bounce", "Breakout", "Gap and Go"]
        )
    
    # Date range
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now() - timedelta(days=30)
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            datetime.now()
        )
    
    # Strategy Parameters
    st.subheader("Strategy Parameters")
    
    # Different parameters based on strategy
    if strategy_type == "Moving Average Crossover":
        col1, col2 = st.columns(2)
        
        with col1:
            fast_ma = st.number_input("Fast Moving Average Period", min_value=5, max_value=50, value=9)
        
        with col2:
            slow_ma = st.number_input("Slow Moving Average Period", min_value=10, max_value=200, value=21)
            
        strategy_params = {
            "fast_period": fast_ma,
            "slow_period": slow_ma
        }
        
    elif strategy_type == "RSI Reversal":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rsi_period = st.number_input("RSI Period", min_value=5, max_value=30, value=14)
        
        with col2:
            overbought = st.number_input("Overbought Level", min_value=60, max_value=90, value=70)
        
        with col3:
            oversold = st.number_input("Oversold Level", min_value=10, max_value=40, value=30)
            
        strategy_params = {
            "rsi_period": rsi_period,
            "overbought": overbought,
            "oversold": oversold
        }
        
    elif strategy_type == "VWAP Bounce":
        vwap_deviation = st.slider("VWAP Deviation (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.1)
        
        strategy_params = {
            "vwap_deviation": vwap_deviation
        }
        
    elif strategy_type == "Breakout":
        col1, col2 = st.columns(2)
        
        with col1:
            breakout_period = st.number_input("Breakout Period (Days)", min_value=1, max_value=30, value=5)
        
        with col2:
            volume_factor = st.number_input("Volume Factor", min_value=1.0, max_value=5.0, value=2.0, step=0.1)
            
        strategy_params = {
            "breakout_period": breakout_period,
            "volume_factor": volume_factor
        }
        
    elif strategy_type == "Gap and Go":
        col1, col2 = st.columns(2)
        
        with col1:
            min_gap = st.number_input("Minimum Gap Size (%)", min_value=0.5, max_value=10.0, value=1.0, step=0.1)
        
        with col2:
            entry_time = st.selectbox("Entry Time After Open", ["5 min", "10 min", "15 min", "30 min"], index=1)
            
        strategy_params = {
            "min_gap": min_gap,
            "entry_time": entry_time
        }
    
    # Risk management
    st.subheader("Risk Management Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stop_loss = st.number_input("Stop Loss (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    
    with col2:
        take_profit = st.number_input("Take Profit (%)", min_value=0.5, max_value=20.0, value=5.0, step=0.1)
    
    with col3:
        position_size = st.number_input("Position Size (%)", min_value=1, max_value=100, value=10)
    
    risk_params = {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size
    }
    
    backtest_button = st.button("Run Backtest")
    
    if backtest_button and stock_input:
        with st.spinner(f"Backtesting {strategy_type} strategy on {stock_input}..."):
            # Run backtest
            backtest_results = backtest_strategy(
                stock_input,
                strategy_type,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                strategy_params,
                risk_params
            )
            
            if backtest_results:
                # Display backtest results
                display_strategy_results(backtest_results)
            else:
                st.error("Backtesting failed. Please check your inputs and try again.")

# Paper Trading page
elif page == "Paper Trading":
    st.header("Paper Trading Simulator")
    
    # Initialize or get paper trading simulator
    simulator = PaperTradingSimulator(
        initial_balance=st.session_state.account_balance,
        trades=st.session_state.paper_trades,
        trade_history=st.session_state.trade_history
    )
    
    # Paper Trading Interface
    tab1, tab2, tab3 = st.tabs(["Trade", "Positions", "Trade History"])
    
    with tab1:
        st.subheader("New Trade")
        
        col1, col2 = st.columns(2)
        
        with col1:
            trade_symbol = st.text_input("Symbol", "").upper()
            trade_type = st.radio("Trade Type", ["Buy", "Sell Short"], horizontal=True)
            trade_quantity = st.number_input("Quantity (Shares)", min_value=1, value=100)
        
        with col2:
            trade_price = st.number_input("Price per Share ($)", min_value=0.01, value=150.0, step=0.01)
            st.metric("Estimated Total", f"${trade_price * trade_quantity:.2f}")
            
            # Risk management options
            use_stop_loss = st.checkbox("Use Stop Loss")
            if use_stop_loss:
                if trade_type == "Buy":
                    stop_loss = st.number_input("Stop Loss Price ($)", min_value=0.01, max_value=trade_price, value=trade_price*0.95, step=0.01)
                else:
                    stop_loss = st.number_input("Stop Loss Price ($)", min_value=trade_price, value=trade_price*1.05, step=0.01)
            else:
                stop_loss = None
                
            use_take_profit = st.checkbox("Use Take Profit")
            if use_take_profit:
                if trade_type == "Buy":
                    take_profit = st.number_input("Take Profit Price ($)", min_value=trade_price, value=trade_price*1.05, step=0.01)
                else:
                    take_profit = st.number_input("Take Profit Price ($)", min_value=0.01, max_value=trade_price, value=trade_price*0.95, step=0.01)
            else:
                take_profit = None
        
        # Place trade button
        place_trade_button = st.button("Place Trade")
        
        if place_trade_button and trade_symbol and trade_quantity > 0:
            # Validate trade
            trade_result = simulator.place_trade(
                symbol=trade_symbol,
                trade_type=trade_type.lower().replace(" ", "_"),
                quantity=trade_quantity,
                price=trade_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if trade_result['success']:
                st.success(trade_result['message'])
                
                # Log trade
                log_trade(
                    simulator.trade_history[-1],
                    balance_after=simulator.balance
                )
                
                # Update session state
                st.session_state.paper_trades = simulator.trades
                st.session_state.account_balance = simulator.balance
                st.session_state.trade_history = simulator.trade_history
                
                # Save data
                save_current_data()
            else:
                st.error(trade_result['message'])
    
    with tab2:
        st.subheader("Current Positions")
        
        # Display account summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Account Balance", f"${simulator.balance:.2f}")
        with col2:
            st.metric("Open Positions", len([t for t in simulator.trades if t['status'] == 'open']))
        with col3:
            # Calculate unrealized P&L
            unrealized_pnl = 0
            for trade in simulator.trades:
                if trade['status'] == 'open':
                    # Get current price
                    try:
                        current_data = fetch_stock_data(trade['symbol'], period="1d")
                        current_price = current_data['Close'].iloc[-1]
                        
                        if trade['trade_type'] == 'buy':
                            trade_pnl = (current_price - trade['price']) * trade['quantity']
                        else:  # short
                            trade_pnl = (trade['price'] - current_price) * trade['quantity']
                            
                        unrealized_pnl += trade_pnl
                    except:
                        pass
            
            st.metric("Unrealized P&L", f"${unrealized_pnl:.2f}", 
                      f"{unrealized_pnl / simulator.initial_balance * 100:.2f}%" if simulator.initial_balance > 0 else "0.00%")
        
        # Display watchlist
        watchlist = [t for t in simulator.trades if t['status'] == 'watchlist']
        if watchlist:
            st.subheader("Watchlist")
            
            for i, trade in enumerate(watchlist):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{trade['symbol']}**")
                    st.caption(f"Added on {trade['date_added']}")
                
                with col2:
                    # Get current price
                    try:
                        current_data = fetch_stock_data(trade['symbol'], period="1d")
                        current_price = current_data['Close'].iloc[-1]
                        price_change = ((current_price / trade['price']) - 1) * 100
                        st.metric("Current Price", f"${current_price:.2f}", f"{price_change:.2f}%")
                    except:
                        st.metric("Price", f"${trade['price']:.2f}")
                
                with col3:
                    # Trade buttons
                    buy_col, sell_col = st.columns(2)
                    with buy_col:
                        if st.button("Buy", key=f"buy_{i}"):
                            st.session_state.trade_symbol = trade['symbol']
                            st.session_state.trade_price = current_price
                            st.rerun()
                    with sell_col:
                        if st.button("Short", key=f"short_{i}"):
                            st.session_state.trade_symbol = trade['symbol']
                            st.session_state.trade_price = current_price
                            st.session_state.trade_type = "Sell Short"
                            st.rerun()
        
        # Display open positions
        open_trades = [t for t in simulator.trades if t['status'] == 'open']
        if open_trades:
            st.subheader("Open Positions")
            
            for i, trade in enumerate(open_trades):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{trade['symbol']} - {'Long' if trade['trade_type'] == 'buy' else 'Short'}**")
                    st.caption(f"Opened on {trade['date_opened']} at ${trade['price']:.2f}")
                    
                    # Show stop loss and take profit if set
                    if 'stop_loss' in trade and trade['stop_loss']:
                        st.caption(f"Stop Loss: ${trade['stop_loss']:.2f}")
                    if 'take_profit' in trade and trade['take_profit']:
                        st.caption(f"Take Profit: ${trade['take_profit']:.2f}")
                
                with col2:
                    # Get current price and P&L
                    try:
                        current_data = fetch_stock_data(trade['symbol'], period="1d")
                        current_price = current_data['Close'].iloc[-1]
                        
                        if trade['trade_type'] == 'buy':
                            trade_pnl = (current_price - trade['price']) * trade['quantity']
                            pnl_pct = ((current_price / trade['price']) - 1) * 100
                        else:  # short
                            trade_pnl = (trade['price'] - current_price) * trade['quantity']
                            pnl_pct = ((trade['price'] / current_price) - 1) * 100
                            
                        st.metric("Current P&L", f"${trade_pnl:.2f}", f"{pnl_pct:.2f}%")
                    except:
                        st.metric("P&L", "N/A")
                
                with col3:
                    st.metric("Shares", trade['quantity'])
                    
                    # Calculate position value
                    try:
                        position_value = current_price * trade['quantity']
                        st.metric("Value", f"${position_value:.2f}")
                    except:
                        st.metric("Value", f"${trade['price'] * trade['quantity']:.2f}")
                
                with col4:
                    # Close position button
                    if st.button("Close Position", key=f"close_{i}"):
                        close_result = simulator.close_position(
                            position_idx=simulator.get_position_index(trade),
                            price=current_price
                        )
                        
                        if close_result['success']:
                            st.success(close_result['message'])
                            
                            # Update session state
                            st.session_state.paper_trades = simulator.trades
                            st.session_state.account_balance = simulator.balance
                            st.session_state.trade_history = simulator.trade_history
                            
                            # Save data
                            save_current_data()
                            
                            # Rerun to refresh
                            st.rerun()
                        else:
                            st.error(close_result['message'])
        
        if not watchlist and not open_trades:
            st.info("You don't have any positions or watchlist items yet. Use the Trade tab to create new positions.")
    
    with tab3:
        st.subheader("Trade History")
        
        # Display trade history
        if simulator.trade_history:
            # Create DataFrame for better display
            history_df = pd.DataFrame(simulator.trade_history)
            
            # Add additional metrics
            history_df['holding_period'] = history_df.apply(
                lambda row: "N/A" if 'date_closed' not in row or not row['date_closed'] 
                else (datetime.strptime(row['date_closed'], '%Y-%m-%d %H:%M:%S') - 
                     datetime.strptime(row['date_opened'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600,
                axis=1
            )
            
            # Format columns
            history_df['date_opened'] = pd.to_datetime(history_df['date_opened'])
            if 'date_closed' in history_df.columns:
                history_df['date_closed'] = pd.to_datetime(history_df['date_closed'])
            
            # Display dataframe with most recent trades first
            st.dataframe(history_df.sort_values('date_opened', ascending=False))
            
            # Calculate and display performance metrics
            st.subheader("Performance Metrics")
            
            closed_trades = [t for t in simulator.trade_history if 'date_closed' in t and t['date_closed']]
            
            if closed_trades:
                win_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
                loss_trades = [t for t in closed_trades if t.get('pnl', 0) <= 0]
                
                win_rate = len(win_trades) / len(closed_trades) * 100 if closed_trades else 0
                
                total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
                avg_profit = sum(t.get('pnl', 0) for t in win_trades) / len(win_trades) if win_trades else 0
                avg_loss = sum(t.get('pnl', 0) for t in loss_trades) / len(loss_trades) if loss_trades else 0
                
                profit_factor = abs(sum(t.get('pnl', 0) for t in win_trades) / 
                                sum(t.get('pnl', 0) for t in loss_trades)) if loss_trades and sum(t.get('pnl', 0) for t in loss_trades) != 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Win Rate", f"{win_rate:.2f}%")
                    st.metric("Total Trades", len(closed_trades))
                
                with col2:
                    st.metric("Net P&L", f"${total_pnl:.2f}")
                    st.metric("Avg. Profit", f"${avg_profit:.2f}")
                
                with col3:
                    st.metric("Profit Factor", f"{profit_factor:.2f}")
                    st.metric("Avg. Loss", f"${avg_loss:.2f}")
                
                with col4:
                    st.metric("Win Trades", len(win_trades))
                    st.metric("Loss Trades", len(loss_trades))
                
                # Plot performance chart
                st.subheader("Performance Chart")
                
                # Sort trades by date
                sorted_trades = sorted(closed_trades, key=lambda x: x['date_closed'])
                
                # Create cumulative P&L
                cumulative_pnl = []
                running_total = 0
                dates = []
                
                for trade in sorted_trades:
                    running_total += trade.get('pnl', 0)
                    cumulative_pnl.append(running_total)
                    dates.append(trade['date_closed'])
                
                # Create DataFrame for chart
                performance_df = pd.DataFrame({
                    'Date': pd.to_datetime(dates),
                    'Cumulative P&L': cumulative_pnl
                })
                
                # Plot
                fig = px.line(
                    performance_df,
                    x='Date',
                    y='Cumulative P&L',
                    title='Cumulative P&L Over Time'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No closed trades yet. Complete some trades to see performance metrics.")
        else:
            st.info("No trade history yet. Use the Trade tab to create new positions.")

# Performance Analytics page
elif page == "Performance Analytics":
    st.header("Performance Analytics")
    
    # Display performance metrics
    if st.session_state.trade_history:
        display_performance_metrics(st.session_state.trade_history)
    else:
        st.info("No trade history available. Complete some paper trades to see performance analytics.")

# Save data on app close
try:
    save_current_data()
except:
    pass