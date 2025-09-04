import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import numpy as np

# App configuration
st.set_page_config(
    page_title="Options Catalyst Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; font-weight: 700;}
    .section-header {font-size: 1.8rem; color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 0.3rem;}
    .positive {color: #2e8b57; font-weight: 600;}
    .negative {color: #dc143c; font-weight: 600;}
    .neutral {color: #ff8c00; font-weight: 600;}
    .info-box {background-color: #f0f8ff; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin: 10px 0;}
    .risk-high {background-color: #ffcccc; padding: 10px; border-radius: 5px; border-left: 5px solid #dc143c;}
    .risk-medium {background-color: #fff0cc; padding: 10px; border-radius: 5px; border-left: 5px solid #ff8c00;}
    .risk-low {background-color: #ccffcc; padding: 10px; border-radius: 5px; border-left: 5px solid #2e8b57;}
</style>
""", unsafe_allow_html=True)

# App title
st.markdown('<p class="main-header">📈 Options Catalyst Scanner</p>', unsafe_allow_html=True)
st.markdown("Identify potential risks for PUT credit spread strategies by analyzing upcoming catalysts")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    ticker = st.text_input("Stock Ticker", "ABNB").upper()
    dte = st.slider("Days to Expiration (DTE)", min_value=5, max_value=45, value=14)
    st.markdown("---")
    st.markdown("### How to Use")
    st.info("This app helps identify potential risks for selling PUT credit spreads by analyzing:")
    st.info("- Upcoming earnings dates\n- Investor events\n- Technical levels\n- Volatility metrics\n- Recent news sentiment")
    st.markdown("---")
    st.caption("Disclaimer: This is for educational purposes only. Not financial advice.")

# Function to get stock data
@st.cache_data(ttl=3600)
def get_stock_data(ticker, period="6mo"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    info = stock.info
    return hist, info

# Function to get upcoming events
def get_upcoming_events(ticker):
    # In a real app, you would use a financial API for this data
    # For demonstration, we'll use mock data
    today = datetime.date.today()
    
    events = []
    # Mock earnings dates (some random dates in the next 30 days)
    potential_dates = [
        today + timedelta(days=5),
        today + timedelta(days=15),
        today + timedelta(days=22),
        today + timedelta(days=30)
    ]
    
    # Select one random earnings date for the mock data
    import random
    earnings_date = random.choice(potential_dates)
    events.append({
        'date': earnings_date,
        'event': 'Earnings Release',
        'importance': 'High'
    })
    
    # Add investor day if applicable (mock)
    if ticker == "ABNB":
        investor_day = datetime.date(2025, 9, 10)
        if investor_day > today:
            events.append({
                'date': investor_day,
                'event': 'Investor Day',
                'importance': 'High'
            })
    
    # Add Fed meeting (mock)
    fed_meeting = datetime.date(2025, 9, 17)
    if fed_meeting > today:
        events.append({
            'date': fed_meeting,
            'event': 'Fed Meeting',
            'importance': 'Medium'
        })
    
    # Sort events by date
    events.sort(key=lambda x: x['date'])
    return events

# Function to get recent news
@st.cache_data(ttl=3600)
def get_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        return news[:5]  # Return top 5 news items
    except:
        return []

# Function to calculate support/resistance levels
def calculate_support_resistance(hist, num_levels=3):
    closes = hist['Close']
    # Simple pivot point calculation
    pivot = (hist['High'].max() + hist['Low'].min() + closes.iloc[-1]) / 3
    support1 = (2 * pivot) - hist['High'].max()
    resistance1 = (2 * pivot) - hist['Low'].min()
    support2 = pivot - (hist['High'].max() - hist['Low'].min())
    resistance2 = pivot + (hist['High'].max() - hist['Low'].min())
    
    return {
        'pivot': pivot,
        'support': [support1, support2],
        'resistance': [resistance1, resistance2]
    }

# Function to calculate IV percentile
def calculate_iv_percentile(ticker):
    # Mock IV calculation - in a real app, you'd use options data
    # Returning a random value for demonstration
    import random
    return random.randint(30, 80)

# Function to assess risk
def assess_risk(events, dte, current_price, support_levels, iv_percentile):
    risk_score = 0
    reasons = []
    
    # Check for high-impact events within DTE
    for event in events:
        days_until_event = (event['date'] - datetime.date.today()).days
        if 0 <= days_until_event <= dte:
            risk_score += 40 if event['importance'] == 'High' else 20
            reasons.append(f"Upcoming {event['event']} in {days_until_event} days")
    
    # Check distance to support
    closest_support = min(support_levels, key=lambda x: abs(x - current_price))
    support_distance_pct = (current_price - closest_support) / current_price * 100
    
    if support_distance_pct < 2:
        risk_score += 30
        reasons.append(f"Close to support level (${closest_support:.2f})")
    elif support_distance_pct < 5:
        risk_score += 15
        reasons.append(f"Moderately close to support level (${closest_support:.2f})")
    
    # Check IV percentile
    if iv_percentile > 70:
        risk_score -= 10  # High IV is good for premium sellers
        reasons.append("High IV percentile good for option selling")
    elif iv_percentile < 30:
        risk_score += 10
        reasons.append("Low IV percentile means less premium")
    
    # Determine risk level
    if risk_score >= 50:
        risk_level = "High"
    elif risk_score >= 25:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    return risk_level, risk_score, reasons

# Main app logic
def main():
    # Load data
    hist, info = get_stock_data(ticker)
    if hist.empty:
        st.error(f"Could not load data for ticker {ticker}. Please check the ticker symbol and try again.")
        return
    
    current_price = hist['Close'].iloc[-1]
    events = get_upcoming_events(ticker)
    news = get_news(ticker)
    levels = calculate_support_resistance(hist)
    iv_percentile = calculate_iv_percentile(ticker)
    
    # Assess risk
    risk_level, risk_score, risk_reasons = assess_risk(
        events, dte, current_price, levels['support'], iv_percentile
    )
    
    # Layout
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown(f'<p class="section-header">{ticker} Overview</p>', unsafe_allow_html=True)
        st.metric("Current Price", f"${current_price:.2f}")
        st.metric("IV Percentile", f"{iv_percentile}%")
        
        # Display risk assessment
        st.markdown(f'<p class="section-header">Risk Assessment</p>', unsafe_allow_html=True)
        if risk_level == "High":
            st.markdown(f'<div class="risk-high"><h3>High Risk</h3><p>Score: {risk_score}/100</p></div>', unsafe_allow_html=True)
        elif risk_level == "Medium":
            st.markdown(f'<div class="risk-medium"><h3>Medium Risk</h3><p>Score: {risk_score}/100</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="risk-low"><h3>Low Risk</h3><p>Score: {risk_score}/100</p></div>', unsafe_allow_html=True)
        
        for reason in risk_reasons:
            st.write(f"- {reason}")
    
    with col2:
        st.markdown(f'<p class="section-header">Price Chart & Levels</p>', unsafe_allow_html=True)
        
        # Create price chart with support/resistance
        fig = go.Figure()
        
        # Add price data
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name=ticker
        ))
        
        # Add support/resistance lines
        for i, level in enumerate(levels['support']):
            fig.add_hline(y=level, line_dash="dash", line_color="green", 
                         annotation_text=f"S{i+1}", annotation_position="right",
                         annotation_font_color="green")
        
        for i, level in enumerate(levels['resistance']):
            fig.add_hline(y=level, line_dash="dash", line_color="red", 
                         annotation_text=f"R{i+1}", annotation_position="right",
                         annotation_font_color="red")
        
        fig.update_layout(height=400, showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        st.markdown(f'<p class="section-header">Upcoming Catalysts</p>', unsafe_allow_html=True)
        
        today = datetime.date.today()
        for event in events:
            days_away = (event['date'] - today).days
            if days_away >= 0:
                icon = "🔴" if event['importance'] == 'High' else "🟡"
                st.write(f"{icon} **{event['date'].strftime('%b %d, %Y')}** ({days_away} days)")
                st.write(f"{event['event']} - *{event['importance']} Impact*")
                st.markdown("---")
        
        st.markdown(f'<p class="section-header">Recent News</p>', unsafe_allow_html=True)
        for item in news:
            # Extract title and publisher
            title = item.get('title', 'No title')
            publisher = item.get('publisher', 'Unknown')
            link = item.get('link', '#')
            
            # Display news item
            st.write(f"**{title}**")
            st.caption(f"Source: {publisher}")
            st.markdown("---")
    
    # Strategy recommendation
    st.markdown(f'<p class="section-header">PUT Credit Spread Recommendation</p>', unsafe_allow_html=True)
    
    if risk_level == "High":
        st.error("""
        **Not Recommended** - High risk detected due to:
        - Upcoming catalysts that may increase volatility
        - Price near key support levels
        - Consider waiting until after events or choosing a different underlying
        """)
    elif risk_level == "Medium":
        st.warning("""
        **Caution Advised** - Moderate risk detected:
        - Consider smaller position sizes
        - Choose wider spreads for more room
        - Closely monitor positions
        - Consider shorter DTE to avoid upcoming events
        """)
    else:
        st.success("""
        **Favorable Conditions** - Lower risk environment:
        - No major catalysts in the selected DTE period
        - Adequate distance from key support levels
        - Standard position sizing appropriate
        """)
    
    # Additional strategy details
    exp_date = today + timedelta(days=dte)
    st.info(f"""
    **Strategy Details for {dte} DTE (Expiring ~{exp_date.strftime('%b %d, %Y')}):**
    - Suggested short put strike: {round(current_price * 0.95, 2):.2f} (~5% below current price)
    - Suggested long put strike: {round(current_price * 0.90, 2):.2f} (~10% below current price)
    - Width: ${round(current_price * 0.05, 2):.2f}
    - Management: Close at 50% of max profit or if price breaches short strike
    """)

# Run the app
if __name__ == "__main__":
    main()
