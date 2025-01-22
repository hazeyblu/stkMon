import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Fetch Nifty 500 data
nifty_symbol = "^CRSLDX"  # Nifty 500 ticker in yfinance

# Get current week's Monday
today = datetime.today()
monday = today - timedelta(days=today.weekday())

# Read yfinance tickers from CSV
tickers = pd.read_csv("stk.csv", header=None)[0].tolist()

# Fetch data for each ticker
data = []
for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1wk")
        if monday.strftime('%Y-%m-%d') not in hist.index:
            st.warning(f"No data for {ticker} on {monday.strftime('%Y-%m-%d')}")
            continue
        monday_open = hist.loc[monday.strftime('%Y-%m-%d')]['Open']
        last_price = stock.history(period="1d")['Close'].iloc[-1]
        returns = (last_price - monday_open) / monday_open * 100
        display_ticker = ticker.replace(".NS", "")  # Remove .NS from ticker
        data.append([display_ticker, monday_open, last_price, returns])
    except Exception as e:
        st.warning(f"Error fetching data for {ticker}: {e}")

# Fetch Nifty 500 data
nifty = yf.Ticker(nifty_symbol)
nifty_hist = nifty.history(period="1wk")
nifty_monday_open = nifty_hist.loc[monday.strftime('%Y-%m-%d')]['Open']
nifty_last_price = nifty.history(period="1d")['Close'].iloc[-1]
nifty_returns = (nifty_last_price - nifty_monday_open) / nifty_monday_open * 100

# Add Nifty 500 data to the table with a blank row for readability
data.append(["", None, None, None])  # Blank row
data.append(["Nifty 500", nifty_monday_open, nifty_last_price, nifty_returns])  # Replace ^CRSLDX with Nifty 500

# Create DataFrame
df = pd.DataFrame(data, columns=["Ticker", "Open", "Last", "Returns (%)"])

# Calculate Alpha (before adding HTML styling)
basket_returns = df.iloc[:-2]["Returns (%)"].mean()  # Exclude Nifty 500 and blank row
alpha = basket_returns - nifty_returns

# Format the DataFrame (add HTML styling after calculating alpha)
df["Open"] = df["Open"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
df["Last"] = df["Last"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
df["Returns (%)"] = df["Returns (%)"].apply(
    lambda x: f"<span style='color: {'green' if x >= 0 else 'red'};'>{x:.2f}%</span>" if pd.notnull(x) else ""
)

# Streamlit App
st.markdown("<h1 style='text-align: center;'>INTRAWEEK</h1>", unsafe_allow_html=True)

# Display Alpha with color (green for positive, red for negative)
alpha_color = "green" if alpha >= 0 else "red"
st.markdown(f"<h1 style='text-align: center; color: {alpha_color};'>Alpha: {alpha:.2f}%</h1>", unsafe_allow_html=True)

# Display the table with colored returns
st.markdown(df.to_html(index=False, escape=False), unsafe_allow_html=True)
