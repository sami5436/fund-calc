import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

st.set_page_config(page_title="Fund Nowcast", layout="wide")

# LGRRX Top 10 Holdings
LGRRX_TOP_10 = [
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
LGRRX_TOTAL_TOP10_WEIGHT = 64.57

# NT Collective S&P500 Index Fund - Lending Top 10 Holdings
SP500_TOP_10 = [
    {"ticker": "NVDA", "weight": 7.91, "name": "NVIDIA Corp"},
    {"ticker": "MSFT", "weight": 6.69, "name": "Microsoft Corp"},
    {"ticker": "AAPL", "weight": 6.57, "name": "Apple Inc"},
    {"ticker": "AMZN", "weight": 3.70, "name": "Amazon.com Inc"},
    {"ticker": "META", "weight": 2.77, "name": "Meta Platforms"},
    {"ticker": "AVGO", "weight": 2.70, "name": "Broadcom Inc"},
    {"ticker": "GOOGL", "weight": 2.46, "name": "Alphabet Class A"},
    {"ticker": "TSLA", "weight": 2.17, "name": "Tesla Inc"},
    {"ticker": "GOOG", "weight": 1.98, "name": "Alphabet Class C"},
    {"ticker": "BRK-B", "weight": 1.60, "name": "Berkshire Hathaway"}
]
SP500_TOTAL_TOP10_WEIGHT = 38.55

# Fetch stock data
@st.cache_data(ttl=60)
def fetch_stock_data(holdings_list):
    results = []
    cst = pytz.timezone('America/Chicago')
    
    for holding in holdings_list:
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
def calculate_fund_change(holdings_data, total_weight):
    valid = [h for h in holdings_data if h["change"] is not None]
    if not valid:
        return 0
    weighted_change = sum(h["change"] * h["weight"] / 100 for h in valid)
    scaled_change = (weighted_change / total_weight) * 100
    return scaled_change

# Helper for styled dataframe
def create_styled_df(holdings_data):
    df = pd.DataFrame(holdings_data)
    df_display = pd.DataFrame({
        "Stock": df["ticker"] + " - " + df["name"],
        "Weight": df["weight"].apply(lambda x: f"{x:.2f}%"),
        "Price": df["price"].apply(lambda x: f"${x:.2f}" if x else "—"),
        "Change %": df["change"],
        "Last Updated": df["updated"].fillna("—")
    })
    
    def color_cols(row):
        change = row["Change %"]
        styles = [''] * len(row)
        if pd.isna(change):
            return styles
        
        # Consistent colors for both light/dark mode
        if change > 0:
            color = 'background-color: #2ecc71; color: black'  # Green bg, black text
        elif change < 0:
            color = 'background-color: #ff4b4b; color: white'  # Red bg, white text
        else:
            return styles
        
        # Apply to Stock (col 0) and Change % (col 3)
        stock_idx = df_display.columns.get_loc("Stock")
        change_idx = df_display.columns.get_loc("Change %")
        
        styles[stock_idx] = color
        styles[change_idx] = color
        return styles

    styled = df_display.style.apply(color_cols, axis=1)
    styled = styled.format({"Change %": "{:+.2f}%"}, na_rep="—")
    return styled

# Header
st.title("💼 Fund Nowcast")

# Create tabs
tab1, tab2 = st.tabs(["📊 LGRRX", "📈 S&P 500 Index"])

with tab1:
    st.subheader("LGRRX - Loomis Sayles Large Cap Growth Trust")
    st.caption("Class D")
    
    # User input for baseline NAV
    lgrrx_baseline_nav = st.number_input("📌 Enter Last Official NAV", value=73.81, format="%.2f", help="Enter the most recent fund NAV (updates around 11 PM CST)", key="lgrrx_nav")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True, key="lgrrx_refresh"):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner("Loading..."):
        lgrrx_holdings_data = fetch_stock_data(LGRRX_TOP_10)
    
    # Calculate
    lgrrx_fund_change = calculate_fund_change(lgrrx_holdings_data, LGRRX_TOTAL_TOP10_WEIGHT)
    lgrrx_estimated_nav = lgrrx_baseline_nav * (1 + lgrrx_fund_change / 100)
    
    cst = pytz.timezone('America/Chicago')
    now_cst = datetime.now(cst)
    time_str = now_cst.strftime("%I:%M:%S %p CST")
    date_str = now_cst.strftime("%b %d, %Y")
    
    # Display metrics
    st.subheader("Fund Estimate")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Last Official NAV", f"${lgrrx_baseline_nav:.2f}")
    
    with col2:
        st.metric("Estimated NAV Now", f"${lgrrx_estimated_nav:.2f}", 
                 delta=f"{lgrrx_fund_change:+.2f}%")
    
    with col3:
        st.metric("Updated", time_str, delta=date_str, delta_color="off")
    
    st.divider()
    
    # Holdings table
    st.subheader("Top 10 Holdings")
    st.caption(f"Coverage: {LGRRX_TOTAL_TOP10_WEIGHT}% of fund")
    
    st.dataframe(create_styled_df(lgrrx_holdings_data), use_container_width=True, hide_index=True)
    
    st.info("💡 Fund NAV updates around 11 PM CST. This estimates the current NAV based on live stock prices.")

with tab2:
    st.subheader("NT Collective S&P500 Index Fund - Lending")
    st.caption("U.S. Equity | Large Blend | 507 holdings")
    
    # User input for baseline NAV
    sp500_baseline_nav = st.number_input("📌 Enter Last Official NAV", value=65.93, format="%.2f", help="Enter the most recent fund NAV (updates around 11 PM CST)", key="sp500_nav")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True, key="sp500_refresh"):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner("Loading..."):
        sp500_holdings_data = fetch_stock_data(SP500_TOP_10)
    
    # Calculate
    sp500_fund_change = calculate_fund_change(sp500_holdings_data, SP500_TOTAL_TOP10_WEIGHT)
    sp500_estimated_nav = sp500_baseline_nav * (1 + sp500_fund_change / 100)
    
    cst = pytz.timezone('America/Chicago')
    now_cst = datetime.now(cst)
    time_str = now_cst.strftime("%I:%M:%S %p CST")
    date_str = now_cst.strftime("%b %d, %Y")
    
    # Display metrics
    st.subheader("Fund Estimate")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Last Official NAV", f"${sp500_baseline_nav:.2f}")
    
    with col2:
        st.metric("Estimated NAV Now", f"${sp500_estimated_nav:.2f}", 
                 delta=f"{sp500_fund_change:+.2f}%")
    
    with col3:
        st.metric("Updated", time_str, delta=date_str, delta_color="off")
    
    st.divider()
    
    # Holdings table
    st.subheader("Top 10 Holdings")
    st.caption(f"Coverage: {SP500_TOTAL_TOP10_WEIGHT}% of fund (as of 09/30/2025)")
    
    st.dataframe(create_styled_df(sp500_holdings_data), use_container_width=True, hide_index=True)
    
    st.info("💡 Fund NAV updates around 11 PM CST. This estimates the current NAV based on live stock prices.")

st.divider()
st.caption("⚠️ For informational purposes only. Not investment advice.")