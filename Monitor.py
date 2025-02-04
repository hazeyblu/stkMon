from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import pandas as pd
import os

# File to save Monday open prices
OPEN_PRICE_FILE = "monday_open_prices.csv"


# Function to save Monday open prices to a file
def save_monday_open_prices(monday_prices_dict, refresh_date):

    df = pd.DataFrame({
        "Ticker": list(monday_prices_dict.keys()),
        "Monday Open": list(monday_prices_dict.values()),
        "Refresh Date": [refresh_date] * len(monday_prices_dict)
    })
    df.to_csv(OPEN_PRICE_FILE, index=False)


# Function to load Monday open prices from a file
def load_monday_open_prices():
    if os.path.exists(OPEN_PRICE_FILE):
        df = pd.read_csv(OPEN_PRICE_FILE)
        df["Refresh Date"] = pd.to_datetime(df["Refresh Date"])
        return df.set_index("Ticker")[["Monday Open", "Refresh Date"]].to_dict(orient="index")
    return {}


# Function to get the most recent Monday
def get_most_recent_monday():
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    return monday.date()


# Function to fetch the opening price for a ticker on the most recent Monday
def fetch_monday_open_price(ticker):
    try:
        monday = get_most_recent_monday()
        friday = monday - timedelta(days=3)
        data = yf.download(ticker, start=friday, end=monday)
        if not data.empty:
            return data["Open"].iloc[0].iloc[0]
    except Exception as e:
        st.error(f"Error fetching Monday open price for {ticker}: {e}")
    return None


# Function to fetch the latest price for a ticker
def fetch_last_price(ticker):
    try:
        data = yf.download(ticker, period="1d", interval="1d")
        if not data.empty:
            return data["Close"].iloc[0].iloc[0]
    except Exception as e:
        st.error(f"Error fetching latest price for {ticker}: {e}")
    return None


# Function to style returns
def color_returns(val):
    if isinstance(val, str) and val.endswith("%"):
        returns = float(val.strip("%"))
        color = "green" if returns > 0 else "red"
        return f"color: {color}; text-align: right;"
    return ""


# Function to display Alpha
def display_alpha(alpha):
    color = "green" if alpha >= 0 else "red"
    st.markdown(
        f"<h1 style='text-align: center;'>Alpha: <span style='color: {color};'>{alpha:.2f}%</span></h1>",
        unsafe_allow_html=True
    )



# Initialize variables
nifty_symbol = "^CRSLDX"  # Nifty 500 equivalent on Yahoo Finance
today = datetime.today().date()
current_monday = get_most_recent_monday()

# Read tickers from CSV
tickers = pd.read_csv("stk.csv", header=None)[0].tolist()
tickers = [ticker.replace(".NS", "") for ticker in tickers]  # Remove ".NS" for Yahoo Finance compatibility

# Load saved Monday open prices
monday_open_data = load_monday_open_prices()
monday_open_prices = {k: v["Monday Open"] for k, v in monday_open_data.items()}
last_refresh_date = next(iter(monday_open_data.values()), {}).get("Refresh Date", None)


# Refresh Monday open prices if necessary
if last_refresh_date is None or last_refresh_date.date() != current_monday:
    new_monday_open_prices = {}
    for ticker in tickers:
        # Only fetch the Monday open price if it's not already in the file
        if ticker not in monday_open_prices:
            monday_open = fetch_monday_open_price(f"{ticker}.NS")
            if monday_open is not None:
                new_monday_open_prices[ticker] = monday_open

    # Fetch and save Nifty 500 Monday open price if it's not already in the file
    if nifty_symbol not in monday_open_prices:
        nifty_monday_open = fetch_monday_open_price(nifty_symbol)
        if nifty_monday_open is not None:
            new_monday_open_prices[nifty_symbol] = nifty_monday_open

    if new_monday_open_prices:  # Save only if new data is fetched
        save_monday_open_prices(new_monday_open_prices, today)
        monday_open_prices.update(new_monday_open_prices)  # Update the dictionary with new prices


# Function to prepare data for the table
# @st.cache_data(ttl=60)  # Cache the table and update it every 60 seconds
def prepare_table_data():
    data = []
    for ticker in tickers:
        last_price = fetch_last_price(f"{ticker}.NS")
        if last_price is not None:
            last_price = round(last_price, 2)  # Format to 2 decimal places
        monday_open = monday_open_prices.get(ticker)
        if monday_open is not None and last_price is not None:
            # Ensure returns is calculated as a scalar
            returns = ((last_price - monday_open) / monday_open) * 100
            returns = round(float(returns), 2)  # Format to 2 decimal places
            data.append([ticker, round(monday_open, 2), last_price, returns])

    # Fetch Nifty 500 data
    nifty_last_price = fetch_last_price(nifty_symbol)
    nifty_monday_open = float(monday_open_prices.get(nifty_symbol))
    if nifty_monday_open is not None and nifty_last_price is not None:
        nifty_returns = round((nifty_last_price - nifty_monday_open) / nifty_monday_open * 100, 2)
    else:
        nifty_returns = None

    # Calculate basket returns and Alpha
    basket_returns = pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])[
        "Returns (%)"].mean() if data else 0
    alpha = basket_returns - (nifty_returns if nifty_returns is not None else 0)

    # Display Alpha
    display_alpha(alpha)

    # Add summary rows for Intraweek and Nifty 500
    summary_data = [["Intraweek", 0, 0, round(basket_returns, 2)],
                    ["Nifty 500", round(nifty_monday_open, 2), round(nifty_last_price, 2),
                     nifty_returns],
                    ]  # No empty row

    # Add stock data below summary
    data = summary_data + data
    
    return pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"]), alpha

# Get the table data
df, alpha = prepare_table_data()
df["Monday Open"] = df["Monday Open"].apply(lambda x: f"{x:.2f}" if x is not None else None)
df["Last Price"] = df["Last Price"].apply(lambda x: f"{x:.2f}" if x is not None else None)

# Apply color and formatting to the Returns column
df["Returns (%)"] = df["Returns (%)"].apply(lambda x: f"{float(x):.2f}%" if x is not None else None)

# Insert blank row at row number 3 (index 2)
blank_row = pd.DataFrame([["", "", "", ""]], columns=df.columns)  # Blank row
df = pd.concat([df.iloc[:2], blank_row, df.iloc[2:]], ignore_index=True)

st.dataframe(df.style.map(color_returns, subset=["Returns (%)"]), use_container_width=True, hide_index=True)

# Auto-refresh every 60 seconds
st.markdown(
    """
    <script>
    setTimeout(function() {
        window.location.reload();
    }, 60000);  // 60 seconds
    </script>
    """,
    unsafe_allow_html=True
)
