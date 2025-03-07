#dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from stock_data import (
    fetch_stock_data, 
    get_stock_info, 
    calculate_historical_volatility,
    get_premarket_movers,
    get_day_trading_metrics
)

from day_trading_scanner import (
    get_weekly_picks,
    get_sector_performance,
    get_trading_opportunities_by_timeframe
)

from technical_analysis import (
    analyze_stock,
    get_stock_technical_score
)

from market_sentiment import (
    get_market_sentiment,
    get_market_indices,
    get_market_calendar
)

def create_dashboard():
    """
    Create the main dashboard view
    """
    st.header("FalconOne Day Trading Dashboard")
    
    # Market Overview
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("Market Overview")
        
        # Display market indices
        try:
            indices = get_market_indices()
            
            # Create three columns for indices
            idx_col1, idx_col2, idx_col3 = st.columns(3)
            
            with idx_col1:
                if 'S&P 500' in indices:
                    st.metric("S&P 500", 
                              f"{indices['S&P 500']['price']:.2f}", 
                              f"{indices['S&P 500']['change']:.2f}%")
            
            with idx_col2:
                if 'NASDAQ' in indices:
                    st.metric("NASDAQ", 
                              f"{indices['NASDAQ']['price']:.2f}", 
                              f"{indices['NASDAQ']['change']:.2f}%")
            
            with idx_col3:
                if 'Dow Jones' in indices:
                    st.metric("Dow Jones", 
                              f"{indices['Dow Jones']['price']:.2f}", 
                              f"{indices['Dow Jones']['change']:.2f}%")
            
            # Market sentiment gauge
            market_sentiment = get_market_sentiment()
            
            # Map sentiment to color
            sentiment_color = "green" if market_sentiment['overall'] == "Bullish" else \
                             "orange" if market_sentiment['overall'] == "Neutral" else "red"
            
            st.markdown(f"### Market Sentiment: <span style='color:{sentiment_color}'>{market_sentiment['overall']}</span>", 
                       unsafe_allow_html=True)
            
            # Sentiment score gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = market_sentiment['score'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Sentiment Score"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': sentiment_color},
                    'steps': [
                        {'range': [0, 30], 'color': "red"},
                        {'range': [30, 70], 'color': "orange"},
                        {'range': [70, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': market_sentiment['score']
                    }
                }
            ))
            
            fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Could not load market overview: {str(e)}")
    
    with col2:
        st.subheader("Market Calendar")
        
        # Display market calendar events
        try:
            calendar = get_market_calendar()
            
            if calendar:
                for event in calendar[:5]:  # Display top 5 events
                    st.markdown(
                        f"**{event['date']}** - {event['time'] if 'time' in event else ''} "
                        f"<br>{event['event']}", 
                        unsafe_allow_html=True
                    )
                
                if len(calendar) > 5:
                    with st.expander("Show more events"):
                        for event in calendar[5:]:
                            st.markdown(
                                f"**{event['date']}** - {event['time'] if 'time' in event else ''} "
                                f"<br>{event['event']}", 
                                unsafe_allow_html=True
                            )
            else:
                st.info("No upcoming market events")
        except:
            st.info("Market calendar not available")
    
    with col3:
        st.subheader("Trading Day")
        
        # Display current date and time
        now = datetime.now()
        st.markdown(f"**Date:** {now.strftime('%Y-%m-%d')}")
        st.markdown(f"**Time:** {now.strftime('%H:%M:%S')}")
        
        # Market hours indicator
        market_open = 9  # 9:30 AM ET
        market_close = 16  # 4:00 PM ET
        current_hour = now.hour
        
        if current_hour >= market_open and current_hour < market_close:
            st.markdown("**Market Status:** 🟢 Open")
            
            # Calculate time until close
            close_time = datetime(now.year, now.month, now.day, market_close, 0, 0)
            time_to_close = close_time - now
            hours, remainder = divmod(time_to_close.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            st.markdown(f"**Time to Close:** {hours}h {minutes}m")
        else:
            st.markdown("**Market Status:** 🔴 Closed")
            
            # Calculate time until open
            if current_hour >= market_close:  # After close
                next_day = now + timedelta(days=1)
                open_time = datetime(next_day.year, next_day.month, next_day.day, market_open, 30, 0)
            else:  # Before open
                open_time = datetime(now.year, now.month, now.day, market_open, 30, 0)
            
            time_to_open = open_time - now
            hours, remainder = divmod(time_to_open.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            st.markdown(f"**Time to Open:** {hours}h {minutes}m")
    
    # Weekly Top Picks
    st.subheader("Weekly Top Picks for Day Trading")
    
    # Get weekly picks from session state if available
    weekly_picks = None
    if 'weekly_picks' in st.session_state and st.session_state.weekly_picks:
        weekly_picks = pd.DataFrame(st.session_state.weekly_picks)
    else:
        # Generate new picks
        with st.spinner("Generating weekly picks..."):
            weekly_picks = get_weekly_picks()
            if not weekly_picks.empty:
                st.session_state.weekly_picks = weekly_picks.to_dict('records')
                st.session_state.weekly_picks_date = datetime.now().strftime('%Y-%m-%d')
    
    if weekly_picks is not None and not weekly_picks.empty:
        # Display picks in a grid
        cols = st.columns(3)
        
        for i, (_, pick) in enumerate(weekly_picks.head(6).iterrows()):
            with cols[i % 3]:
                # Create card-like display
                st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
                    <h3>{pick['symbol']} - {pick['name']}</h3>
                    <p><strong>Strategy:</strong> {pick['strategy']}</p>
                    <p><strong>Est. Gain:</strong> {pick['estimated_gain']}%</p>
                    <p><strong>Risk Level:</strong> {pick['risk_level']}</p>
                    <p><strong>Best Entry:</strong> {pick['best_entry_time']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Weekly picks are being generated. Please check back later.")
    
    # Pre-market Movers
    st.subheader("Pre-market Movers")
    
    try:
        premarket_data = get_premarket_movers()
        
        if not premarket_data.empty:
            # Format the dataframe
            display_df = premarket_data.copy()
            display_df['Last Close'] = display_df['Last Close'].map('${:,.2f}'.format)
            display_df['Pre-market Price'] = display_df['Pre-market Price'].map('${:,.2f}'.format)
            display_df['Pre-market Change %'] = display_df['Pre-market Change %'].map('{:+.2f}%'.format)
            
            # Split into gainers and losers
            gainers = display_df[display_df['Pre-market Change %'].str.contains('\+')].copy()
            losers = display_df[~display_df['Pre-market Change %'].str.contains('\+')].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Top Gainers")
                if not gainers.empty:
                    st.dataframe(gainers.head(5), hide_index=True)
                else:
                    st.info("No gainers found")
            
            with col2:
                st.markdown("### Top Losers")
                if not losers.empty:
                    st.dataframe(losers.head(5), hide_index=True)
                else:
                    st.info("No losers found")
        else:
            st.info("Pre-market data not available")
    except Exception as e:
        st.warning(f"Could not load pre-market movers: {str(e)}")
    
    # Sector Performance
    st.subheader("Sector Performance")
    
    try:
        sector_data = get_sector_performance()
        
        if not sector_data.empty:
            # Create bar chart
            fig = px.bar(
                sector_data,
                y='Sector',
                x='Daily Change %',
                color='Daily Change %',
                color_continuous_scale='RdYlGn',
                title='Sector Daily Performance',
                labels={'Daily Change %': 'Change (%)', 'Sector': ''},
                orientation='h'
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display top performing sector
            top_sector = sector_data.iloc[0]
            st.markdown(f"""
            **Top Performing Sector:** {top_sector['Sector']} ({top_sector['Daily Change %']:.2f}%)
            """)
        else:
            st.info("Sector performance data not available")
    except Exception as e:
        st.warning(f"Could not load sector performance: {str(e)}")
    
    # Trading Opportunities By Timeframe
    st.subheader("Trading Opportunities By Time of Day")
    
    try:
        opportunities = get_trading_opportunities_by_timeframe()
        
        if opportunities:
            # Create tabs for each timeframe
            tab_names = {
                'opening_range_breakout': 'Opening Range Breakout',
                'midday_momentum': 'Midday Momentum',
                'power_hour': 'Power Hour',
                'closing_auction': 'Closing Auction'
            }
            
            tabs = st.tabs(list(tab_names.values()))
            
            for i, (key, name) in enumerate(tab_names.items()):
                with tabs[i]:
                    if opportunities[key]:
                        # Create a dataframe
                        df = pd.DataFrame(opportunities[key])
                        
                        # Display stocks in this timeframe category
                        st.dataframe(df, hide_index=True)
                        
                        # Display strategy info
                        if key == 'opening_range_breakout':
                            st.markdown("""
                            **Strategy:** Wait for the first 30 minutes of trading to establish a range, 
                            then enter when price breaks above/below this range with increased volume.
                            """)
                        elif key == 'midday_momentum':
                            st.markdown("""
                            **Strategy:** Look for stocks that maintain their trend direction during 
                            typically low-volume midday hours, indicating strong conviction.
                            """)
                        elif key == 'power_hour':
                            st.markdown("""
                            **Strategy:** Enter positions during the final hour of trading when volume 
                            and volatility typically increase, creating strong directional moves.
                            """)
                        elif key == 'closing_auction':
                            st.markdown("""
                            **Strategy:** Position for stocks with institutional interest that may 
                            see significant price moves during the closing auction process.
                            """)
                    else:
                        st.info(f"No {name} opportunities found")
        else:
            st.info("Trading opportunities by timeframe not available")
    except Exception as e:
        st.warning(f"Could not load trading opportunities: {str(e)}")
    
    # Recent Analysis
    st.subheader("Quick Technical Analysis")
    
    # Allow user to enter a stock symbol
    quick_symbol = st.text_input("Enter symbol for quick analysis", "AAPL")
    
    if quick_symbol:
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                # Get stock data
                stock_data = fetch_stock_data(quick_symbol, period="1mo")
                
                if not stock_data.empty:
                    # Create a candlestick chart
                    fig = go.Figure(go.Candlestick(
                        x=stock_data.index,
                        open=stock_data['Open'],
                        high=stock_data['High'],
                        low=stock_data['Low'],
                        close=stock_data['Close'],
                        name='Price'
                    ))
                    
                    # Add a moving average
                    ma20 = stock_data['Close'].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=stock_data.index, 
                        y=ma20,
                        line=dict(color='orange', width=2),
                        name='20-day MA'
                    ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{quick_symbol} - Last Month",
                        xaxis_rangeslider_visible=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Could not fetch data for {quick_symbol}")
            except Exception as e:
                st.error(f"Error creating chart for {quick_symbol}: {str(e)}")
        
        with col2:
            try:
                # Get technical score
                tech_score = get_stock_technical_score(quick_symbol)
                
                if tech_score:
                    # Create gauge chart for technical score
                    score = tech_score['overall_score']
                    rating = tech_score['rating']
                    
                    # Determine color based on score
                    if score >= 70:
                        color = "green"
                    elif score >= 50:
                        color = "orange"
                    else:
                        color = "red"
                    
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=score,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': f"Technical Score: {rating}"},
                        gauge={
                            'axis': {'range': [0, 100]},
                            'bar': {'color': color},
                            'steps': [
                                {'range': [0, 30], 'color': "red"},
                                {'range': [30, 50], 'color': "orange"},
                                {'range': [50, 70], 'color': "yellow"},
                                {'range': [70, 100], 'color': "green"}
                            ],
                            'threshold': {
                                'line': {'color': "black", 'width': 4},
                                'thickness': 0.75,
                                'value': score
                            }
                        }
                    ))
                    
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display score breakdown
                    if 'breakdown' in tech_score:
                        st.subheader("Score Breakdown")
                        
                        # Convert breakdown to DataFrame for display
                        breakdown_df = pd.DataFrame({
                            'Component': tech_score['breakdown'].keys(),
                            'Score': tech_score['breakdown'].values()
                        })
                        
                        # Create horizontal bar chart
                        fig = px.bar(
                            breakdown_df,
                            y='Component',
                            x='Score',
                            orientation='h',
                            color='Score',
                            color_continuous_scale='RdYlGn',
                            range_color=[0, 100]
                        )
                        
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Could not calculate technical score for {quick_symbol}")
            except Exception as e:
                st.error(f"Error analyzing {quick_symbol}: {str(e)}")
    
    # Help and Documentation Section
    with st.expander("📚 How to Use This Dashboard"):
        st.markdown("""
        ## Welcome to the FalconOne Dashboard
        
        This dashboard provides a comprehensive overview of the market and day trading opportunities. Here's how to use the different sections:
        
        ### 1. Market Overview
        - Check the current status of major indices
        - View overall market sentiment
        - Monitor upcoming market events
        
        ### 2. Weekly Top Picks
        - Review our algorithmic picks for the week
        - Each pick includes estimated gain potential and risk level
        - Picks are updated weekly based on technical analysis and market conditions
        
        ### 3. Pre-market Movers
        - See which stocks are moving significantly before market open
        - Identify potential gap-up or gap-down candidates
        
        ### 4. Sector Performance
        - Monitor which sectors are outperforming or underperforming
        - Rotate your trading focus to hot sectors
        
        ### 5. Trading Opportunities By Time of Day
        - Find stocks that typically perform best during specific market hours
        - Optimize your trading schedule based on stock behavior
        
        ### 6. Quick Technical Analysis
        - Get instant technical assessment of any stock
        - View key technical indicators and overall score
        
        Use the navigation sidebar to access more detailed tools including the Day Trading Scanner, Technical Analysis, Strategy Backtester, and Paper Trading simulator.
        """)
    
    # Strategy Insights Section
    with st.expander("🎯 Day Trading Strategy Insights"):
        st.markdown("""
        ## Key Day Trading Strategies
        
        ### Gap and Go
        - **Strategy:** Trade stocks that gap up or down at market open
        - **Best For:** High volatility stocks with news catalysts
        - **Typical Hours:** First 30 minutes after market open
        - **Risk Level:** High
        
        ### Momentum Trading
        - **Strategy:** Trade in the direction of strong price movement
        - **Best For:** Stocks with high relative volume
        - **Typical Hours:** First 2 hours and last hour of trading
        - **Risk Level:** Medium to High
        
        ### VWAP Bounce
        - **Strategy:** Enter when price tests and rebounds from VWAP
        - **Best For:** Liquid stocks in defined trend
        - **Typical Hours:** Mid-morning to early afternoon
        - **Risk Level:** Medium
        
        ### Moving Average Reversal
        - **Strategy:** Enter when price reverses at key moving averages
        - **Best For:** Range-bound or trending stocks
        - **Typical Hours:** Any time during trading day
        - **Risk Level:** Medium
        
        ### Breakout Trading
        - **Strategy:** Enter when price breaks above resistance or below support
        - **Best For:** Stocks forming clear chart patterns
        - **Typical Hours:** Any time during trading day
        - **Risk Level:** Medium to High
        
        ### Risk Management Tips
        1. Never risk more than 1-2% of your account on a single trade
        2. Always use stop losses to limit potential losses
        3. Take partial profits as trades move in your favor
        4. Be mindful of increased volatility around market open/close
        5. Avoid trading during low-volume periods unless you have a specific edge
        """)