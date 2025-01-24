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
        data.append([display_ticker, monday_open, last_price, f"{returns:.2f}%"])
    except Exception as e:
        st.warning(f"Error fetching data for {ticker}: {e}")

# Fetch Nifty 500 data
nifty = yf.Ticker(nifty_symbol)
nifty_hist = nifty.history(period="1wk")
nifty_monday_open = nifty_hist.loc[monday.strftime('%Y-%m-%d')]['Open']
nifty_last_price = nifty.history(period="1d")['Close'].iloc[-1]
nifty_returns = (nifty_last_price - nifty_monday_open) / nifty_monday_open * 100

# Calculate Basket Returns (Intraweek)
basket_returns = pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])["Returns (%)"].str.rstrip('%').astype(float).mean()
alpha = basket_returns - nifty_returns

# Create a new DataFrame with the desired structure
# Add Intraweek (Basket Returns) and Nifty 500 at the top
new_data = [
    ["Intraweek", None, None, f"{basket_returns:.2f}%"],  # Intraweek row
    ["Nifty 500", nifty_monday_open, nifty_last_price, f"{nifty_returns:.2f}%"],  # Nifty 500 row
    ["", None, None, None],  # Blank row
]

# Add individual stock performances
new_data.extend(data)

# Create DataFrame
df = pd.DataFrame(new_data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])

# Format the DataFrame (add HTML styling)
df["Monday Open"] = df["Monday Open"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
df["Last Price"] = df["Last Price"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
df["Returns (%)"] = df["Returns (%)"].apply(
    lambda x: (
        f"<span style='color: {'green' if float(x.strip('%')) >= 0 else 'red'}; text-align: right; display: block;'>{x}</span>"
        if pd.notnull(x) and isinstance(x, str) and x.strip() != ""
        else ""
    )
)

# Streamlit App
# 1. Intraweek Header (Burgundy color)
st.markdown("<h3 style='text-align: center; color: #800020;'>INTRAWEEK</h3>", unsafe_allow_html=True)

# 2. Alpha
alpha_color = "green" if alpha >= 0 else "red"
st.markdown(
    f"<h1 style='text-align: center; color: {alpha_color};'>Alpha: {alpha:.2f}%</h1>",
    unsafe_allow_html=True
)

# 3. Table (with Intraweek row highlighted in pale yellow)
# Add a pale yellow background to the Intraweek row
df_styled = df.style.apply(
    lambda x: ["background-color: #FFFFE0" if x.name == 0 else "" for _ in x], axis=1
)

# Display the table
st.markdown(
    f"""
    <div style="display: flex; justify-content: center;">
        {df_styled.to_html(index=False, escape=False, justify='center')}
    </div>
    """,
    unsafe_allow_html=True
)
