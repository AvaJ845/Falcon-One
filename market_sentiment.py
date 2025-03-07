#market_sentiment.py
import pandas as pd
import numpy as np
import streamlit as st
import random
from datetime import datetime, timedelta

from stock_data import fetch_stock_data

def get_market_sentiment():
    """
    Get overall market sentiment analysis
    
    Returns:
    dict: Dictionary containing sentiment data
    """
    # In a production app, this would analyze real market data
    # For this demo, we'll use simulated data
    
    # Generate a random but somewhat realistic sentiment score (0-100)
    sentiment_score = random.randint(40, 80)
    
    # Determine sentiment label based on score
    if sentiment_score >= 70:
        sentiment_label = "Bullish"
    elif sentiment_score >= 45:
        sentiment_label = "Neutral"
    else:
        sentiment_label = "Bearish"
    
    # Generate additional sentiment metrics
    fear_greed = random.randint(30, 70)
    social_score = random.randint(40, 80)
    news_score = random.randint(40, 80)
    
    # Calculate volatility expectation
    vix_proxy = max(15, min(35, 100 - sentiment_score + random.randint(-10, 10)))
    
    return {
        'overall': sentiment_label,
        'score': sentiment_score,
        'fear_greed': fear_greed,
        'social_score': social_score,
        'news_score': news_score,
        'volatility_expectation': vix_proxy
    }

def analyze_news_sentiment(ticker):
    """
    Analyze news sentiment for a specific stock
    
    Parameters:
    ticker (str): Stock ticker symbol
    
    Returns:
    dict: Dictionary containing news sentiment data
    """
    # In a production app, this would analyze real news data
    # For this demo, we'll use simulated data
    
    # Generate sentiment score (-100 to 100)
    base_sentiment = random.randint(-30, 70)
    
    # Create simulated headlines
    company_name = ticker
    try:
        # Try to get company name from stock info
        stock_data = fetch_stock_data(ticker, period="1d")
        if not stock_data.empty:
            # In a real app, this would get the company name
            # For demo, we'll just use the ticker
            company_name = ticker
    except:
        company_name = ticker
    
    # Generating realistic headlines based on sentiment
    headlines = []
    
    if base_sentiment > 30:  # Positive sentiment
        positive_templates = [
            f"{company_name} Exceeds Quarterly Earnings Expectations",
            f"{company_name} Announces New Product Launch",
            f"Analysts Upgrade {company_name} Stock to 'Buy'",
            f"{company_name} Expands into New Markets",
            f"{company_name} Reports Strong Growth in User Base",
            f"CEO of {company_name} Buys Shares in Show of Confidence"
        ]
        
        for _ in range(3):  # Generate 3 positive headlines
            headline = random.choice(positive_templates)
            headlines.append({
                'title': headline,
                'sentiment': random.uniform(0.3, 0.9),
                'source': random.choice(['Bloomberg', 'CNBC', 'Reuters', 'MarketWatch', 'Wall Street Journal']),
                'date': (datetime.now() - timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')
            })
    
    elif base_sentiment < -10:  # Negative sentiment
        negative_templates = [
            f"{company_name} Misses Earnings Estimates",
            f"{company_name} Announces Layoffs",
            f"Analysts Downgrade {company_name} Stock",
            f"{company_name} Faces Regulatory Investigation",
            f"{company_name} Warns of Revenue Slowdown",
            f"Short Seller Targets {company_name} in New Report"
        ]
        
        for _ in range(3):  # Generate 3 negative headlines
            headline = random.choice(negative_templates)
            headlines.append({
                'title': headline,
                'sentiment': random.uniform(-0.9, -0.3),
                'source': random.choice(['Bloomberg', 'CNBC', 'Reuters', 'MarketWatch', 'Wall Street Journal']),
                'date': (datetime.now() - timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')
            })
    
    else:  # Neutral sentiment
        neutral_templates = [
            f"{company_name} Reports Quarterly Results",
            f"{company_name} Announces Management Changes",
            f"{company_name} Presents at Industry Conference",
            f"{company_name} Maintains Market Share",
            f"Analyst Maintains Neutral Rating on {company_name}",
            f"{company_name} Launches New Initiative"
        ]
        
        for _ in range(3):  # Generate 3 neutral headlines
            headline = random.choice(neutral_templates)
            headlines.append({
                'title': headline,
                'sentiment': random.uniform(-0.2, 0.2),
                'source': random.choice(['Bloomberg', 'CNBC', 'Reuters', 'MarketWatch', 'Wall Street Journal']),
                'date': (datetime.now() - timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')
            })
    
    # Add some mixed headlines regardless of base sentiment
    mixed_templates = [
        f"{company_name} Reports Mixed Results for Q{random.randint(1, 4)}",
        f"{company_name} Restructures Business Operations",
        f"Insider Trading Activity at {company_name}",
        f"{company_name} Adjusts Forecast for Upcoming Quarter",
        f"Analysis: What's Next for {company_name}?",
        f"{company_name} Announces New Partnership"
    ]
    
    for _ in range(2):  # Generate 2 mixed headlines
        headline = random.choice(mixed_templates)
        headlines.append({
            'title': headline,
            'sentiment': random.uniform(-0.5, 0.5),
            'source': random.choice(['Bloomberg', 'CNBC', 'Reuters', 'MarketWatch', 'Wall Street Journal']),
            'date': (datetime.now() - timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')
        })
    
    # Generate sentiment metrics
    avg_sentiment = sum(h['sentiment'] for h in headlines) / len(headlines)
    sentiment_score = int((avg_sentiment + 1) * 50)  # Scale to 0-100
    
    # Determine sentiment label
    if sentiment_score >= 60:
        sentiment_label = "Positive"
    elif sentiment_score >= 40:
        sentiment_label = "Neutral"
    else:
        sentiment_label = "Negative"
    
    return {
        'overall': sentiment_label,
        'score': sentiment_score,
        'headlines': headlines
    }

def get_market_indices():
    """
    Get current market indices data
    
    Returns:
    dict: Dictionary containing index data
    """
    # In a production app, this would fetch real market data
    # For this demo, we'll use simulated data
    
    indices = {
        'S&P 500': {
            'price': 4800 + random.uniform(-50, 50),
            'change': random.uniform(-1.5, 1.5)
        },
        'NASDAQ': {
            'price': 16000 + random.uniform(-100, 100),
            'change': random.uniform(-1.8, 1.8)
        },
        'Dow Jones': {
            'price': 38000 + random.uniform(-200, 200),
            'change': random.uniform(-1.2, 1.2)
        },
        'Russell 2000': {
            'price': 2200 + random.uniform(-30, 30),
            'change': random.uniform(-2.0, 2.0)
        },
        'VIX': {
            'price': 18 + random.uniform(-5, 5),
            'change': random.uniform(-8.0, 8.0)
        }
    }
    
    return indices

def get_market_calendar():
    """
    Get upcoming market events calendar
    
    Returns:
    list: List of upcoming market events
    """
    # In a production app, this would fetch real calendar data
    # For this demo, we'll create a simulated calendar
    
    # Generate dates for the next 10 days
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(10)]
    
    # List of possible events
    economic_events = [
        "Non-Farm Payrolls",
        "FOMC Meeting",
        "CPI Release",
        "GDP Data",
        "Retail Sales",
        "Jobless Claims",
        "ISM Manufacturing",
        "ISM Services",
        "Building Permits",
        "Consumer Confidence"
    ]
    
    earnings_companies = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
        "NVDA",
        "JPM",
        "V",
        "WMT",
        "PG",
        "KO",
        "DIS",
        "NFLX"
    ]
    
    # Generate calendar events
    calendar = []
    
    # Add economic events
    for _ in range(5):
        event_date = random.choice(dates)
        event_time = f"{random.randint(8, 16):02d}:{random.choice(['00', '30'])}"
        event = random.choice(economic_events)
        
        calendar.append({
            'date': event_date,
            'time': event_time,
            'event': f"{event} Economic Data Release",
            'type': 'economic'
        })
    
    # Add earnings events
    for _ in range(8):
        event_date = random.choice(dates)
        before_after = random.choice(['Before Market Open', 'After Market Close'])
        company = random.choice(earnings_companies)
        
        calendar.append({
            'date': event_date,
            'time': before_after,
            'event': f"{company} Earnings",
            'type': 'earnings'
        })
    
    # Add market holidays or special events
    special_events = [
        "Market Holiday: Presidents Day",
        "Market Early Close (1:00 PM)",
        "Fed Chair Speech",
        "Options Expiration",
        "Futures Roll Date"
    ]
    
    for _ in range(1):
        event_date = random.choice(dates)
        event = random.choice(special_events)
        
        calendar.append({
            'date': event_date,
            'event': event,
            'type': 'special'
        })
    
    # Sort by date
    calendar.sort(key=lambda x: x['date'])
    
    return calendar