import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

st.set_page_config(page_title="LGRRX Nowcast", layout="wide")

# Top 10 Holdings
TOP_10 = [
    {"ticker": "NVDA", "weight": 10.14, "name": "NVIDIA"},
    {"ticker": "META", "weight": 8.54, "name": "Meta"},
    {"ticker": "NFLX", "weight": 8.06, "name": "Netflix"},
    {"ticker": "TSLA", "weight": 6.44, "name": "Tesla"},
    {"ticker": "AMZN", "weight": 5.93, "name": "Amazon"},
    {"ticker": "ORCL", "weight": 5.64, "name": "Oracle"},
    {"ticker": "GOOGL", "weight": 5.33, "name": "Alphabet"},
    {"ticker": "V", "weight": 5.13, "name": "Visa"},
    {"ticker": "BA", "weight": 4.74, "name": "Boeing"},
    {"ticker": "MSFT", "weight": 4.63, "name": "Microsoft"}
]

TOTAL_TOP10_WEIGHT = 64.57

# Fetch stock data
@st.cache_data(ttl=60)
def fetch_stock_data():
    results = []
    cst = pytz.timezone('America/Chicago')
    
    for holding in TOP_10:
        try:
            ticker = yf.Ticker(holding["ticker"])
            
            # Get intraday data
            data = ticker.history(period="1d", interval="1m")
            
            current_price = None
            update_time = None
            
            if not data.empty:
                current_price = float(data['Close'].iloc[-1])
                update_time = data.index[-1].tz_convert(cst).strftime("%I:%M %p CST")
            
            # Get previous close
            prev_close = None
            try:
                prev_close = ticker.info.get('previousClose')
            except:
                pass
            
            if prev_close is None:
                hist = ticker.history(period="5d")
                if len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
            
            change_pct = None
            if current_price and prev_close:
                change_pct = ((current_price - prev_close) / prev_close) * 100
            
            results.append({
                "ticker": holding["ticker"],
                "name": holding["name"],
                "weight": holding["weight"],
                "price": current_price,
                "change": change_pct,
                "updated": update_time
            })
        except:
            results.append({
                "ticker": holding["ticker"],
                "name": holding["name"],
                "weight": holding["weight"],
                "price": None,
                "change": None,
                "updated": None
            })
    return results

# Calculate fund impact
def calculate_fund_change(holdings_data):
    valid = [h for h in holdings_data if h["change"] is not None]
    if not valid:
        return 0
    weighted_change = sum(h["change"] * h["weight"] / 100 for h in valid)
    scaled_change = (weighted_change / TOTAL_TOP10_WEIGHT) * 100
    return scaled_change

# Header
st.title("💼 LGRRX Nowcast")
st.caption("Loomis Sayles Large Cap Growth Trust - Class D")

# Create tabs
tab1, tab2 = st.tabs(["📊 Live View", "✏️ Manual Override"])

with tab1:
    # User input for baseline NAV
    baseline_nav = st.number_input("📌 Enter Last Official NAV", value=73.81, format="%.2f", help="Enter the most recent fund NAV (updates around 11 PM CST)")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner("Loading..."):
        holdings_data = fetch_stock_data()
    
    # Calculate
    fund_change = calculate_fund_change(holdings_data)
    estimated_nav = baseline_nav * (1 + fund_change / 100)
    
    cst = pytz.timezone('America/Chicago')
    now_cst = datetime.now(cst)
    time_str = now_cst.strftime("%I:%M:%S %p CST")
    
    # Display metrics
    st.subheader("Fund Estimate")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Last Official NAV", f"${baseline_nav:.2f}")
    
    with col2:
        st.metric("Estimated NAV Now", f"${estimated_nav:.2f}", 
                 delta=f"{fund_change:+.2f}%")
    
    with col3:
        st.metric("Updated", time_str)
    
    st.divider()
    
    # Holdings table - simplified to just 3 columns
    st.subheader("Top 10 Holdings")
    
    df = pd.DataFrame(holdings_data)
    df_display = pd.DataFrame({
        "Stock": df["ticker"] + " - " + df["name"],
        "Price": df["price"].apply(lambda x: f"${x:.2f}" if x else "—"),
        "Change %": df["change"].apply(lambda x: f"{x:+.2f}%" if x is not None else "—"),
        "Last Updated": df["updated"].fillna("—")
    })
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    st.info("💡 Fund NAV updates around 11 PM CST. This estimates the current NAV based on live stock prices.")

with tab2:
    st.subheader("Manual Override")
    st.write("Enter custom stock prices to calculate estimated NAV")
    
    # Get base data
    holdings_data_manual = fetch_stock_data()
    
    manual_baseline = st.number_input("Starting NAV", value=73.81, format="%.2f")
    
    st.divider()
    
    # Simple price input only
    manual_holdings = []
    for i, holding in enumerate(holdings_data_manual):
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.write(f"**{holding['ticker']}** - {holding['name']} ({holding['weight']:.2f}%)")
        
        with col2:
            current = holding['price'] if holding['price'] else 0
            new_price = st.number_input(
                "Price",
                value=float(current),
                format="%.2f",
                key=f"manual_{holding['ticker']}",
                label_visibility="collapsed"
            )
        
        # Get prev close from original data
        try:
            ticker = yf.Ticker(holding['ticker'])
            prev_close = ticker.info.get('previousClose')
        except:
            prev_close = None
        
        change_pct = None
        if new_price and prev_close and prev_close > 0:
            change_pct = ((new_price - prev_close) / prev_close) * 100
        
        manual_holdings.append({
            "ticker": holding["ticker"],
            "weight": holding["weight"],
            "change": change_pct
        })
    
    st.divider()
    
    # Calculate
    manual_fund_change = calculate_fund_change(manual_holdings)
    manual_estimated_nav = manual_baseline * (1 + manual_fund_change / 100)
    
    st.subheader("Result")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Estimated Change", f"{manual_fund_change:+.2f}%")
    with col2:
        st.metric("Estimated NAV", f"${manual_estimated_nav:.2f}")

st.divider()
st.caption("⚠️ For informational purposes only. Not investment advice.")