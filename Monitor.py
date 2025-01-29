from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import pandas as pd
import os
# from streamlit_extras.app_refresh import st_autorefresh


# File to save Monday open prices
OPEN_PRICE_FILE = "monday_open_prices.csv"


def save_monday_open_prices(monday_prices_dict, refresh_date):
    """
    Save Monday open prices to a CSV file.
    
    Args:
        monday_prices_dict (dict): Dictionary of tickers and their Monday open prices.
        refresh_date (datetime.date): Date when the prices were refreshed.
    """
    df = pd.DataFrame({
        "Ticker": list(monday_prices_dict.keys()),
        "Monday Open": list(monday_prices_dict.values()),
        "Refresh Date": [refresh_date] * len(monday_prices_dict)
    })
    df.to_csv(OPEN_PRICE_FILE, index=False)


def load_monday_open_prices():
    """
    Load Monday open prices from a CSV file.
    
    Returns:
        dict: Dictionary with tickers as keys and Monday open prices & refresh dates as values.
    """
    if os.path.exists(OPEN_PRICE_FILE):
        df = pd.read_csv(OPEN_PRICE_FILE)
        df["Refresh Date"] = pd.to_datetime(df["Refresh Date"])
        return df.set_index("Ticker")[["Monday Open", "Refresh Date"]].to_dict(orient="index")
    return {}


def get_most_recent_monday():
    """
    Get the most recent Monday's date.
    
    Returns:
        datetime.date: Date of the most recent Monday.
    """
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    return monday.date()


def fetch_monday_open_price(ticker):
    """
    Fetch the opening price of a stock on the most recent Monday.
    
    Args:
        ticker (str): Stock ticker symbol.
    
    Returns:
        float or None: The Monday opening price or None if unavailable.
    """
    try:
        monday = get_most_recent_monday()
        friday = monday - timedelta(days=3)
        data = yf.download(ticker, start=friday, end=monday)
        if not data.empty:
            return data["Open"].iloc[0].iloc[0]
    except Exception as e:
        st.error(f"Error fetching Monday open price for {ticker}: {e}")
    return None


def fetch_last_price(ticker):
    """
    Fetch the latest closing price of a stock.
    
    Args:
        ticker (str): Stock ticker symbol.
    
    Returns:
        float or None: The latest closing price or None if unavailable.
    """
    try:
        data = yf.download(ticker, period="1d", interval="1d")
        if not data.empty:
            return data["Close"].iloc[0].iloc[0]
    except Exception as e:
        st.error(f"Error fetching latest price for {ticker}: {e}")
    return None


def color_returns(val):
    """
    Apply color styling to return values in the dataframe.
    
    Args:
        val (str): Return value as a percentage string.
    
    Returns:
        str: CSS styling for color formatting.
    """
    if isinstance(val, str) and val.endswith("%"):
        returns = float(val.strip("%"))
        color = "green" if returns > 0 else "red"
        return f"color: {color}; text-align: right;"
    return ""


def display_alpha(alpha):
    """
    Display the calculated alpha value on the Streamlit app.
    
    Args:
        alpha (float): The alpha value to be displayed.
    """
    color = "green" if alpha >= 0 else "red"
    st.markdown(
        f"<h1 style='text-align: center;'>Alpha: <span style='color: {color};'>{alpha:.2f}%</span></h1>",
        unsafe_allow_html=True
    )


nifty_symbol = "^CRSLDX"
today = datetime.today().date()
current_monday = get_most_recent_monday()

# Read tickers from CSV
tickers = pd.read_csv("stk.csv", header=None)[0].tolist()
tickers = [ticker.replace(".NS", "") for ticker in tickers]

# Load saved Monday open prices
monday_open_data = load_monday_open_prices()
monday_open_prices = {k: v["Monday Open"] for k, v in monday_open_data.items()}
last_refresh_date = next(iter(monday_open_data.values()), {}).get("Refresh Date", None)

if last_refresh_date is None or last_refresh_date.date() != current_monday:
    new_monday_open_prices = {}
    for ticker in tickers:
        if ticker not in monday_open_prices:
            monday_open = fetch_monday_open_price(f"{ticker}.NS")
            if monday_open is not None:
                new_monday_open_prices[ticker] = monday_open
    
    if nifty_symbol not in monday_open_prices:
        nifty_monday_open = fetch_monday_open_price(nifty_symbol)
        if nifty_monday_open is not None:
            new_monday_open_prices[nifty_symbol] = nifty_monday_open
    
    if new_monday_open_prices:
        monday_open_prices.update(new_monday_open_prices)
        save_monday_open_prices(monday_open_prices, today)


# Function to prepare data for the table
def prepare_table_data():
    """
    Prepare stock data for display in a table, including returns and alpha calculation.
    
    Returns:
        pd.DataFrame: Dataframe with stock details.
        float: Alpha value.
    """
    data = []
    for ticker in tickers:
        last_price = fetch_last_price(f"{ticker}.NS")
        monday_open = monday_open_prices.get(ticker)
        if monday_open is not None and last_price is not None:
            returns = round(((last_price - monday_open) / monday_open) * 100, 2)
            data.append([ticker, round(monday_open, 2), round(last_price, 2), returns])
    
    nifty_last_price = fetch_last_price(nifty_symbol)
    nifty_monday_open = monday_open_prices.get(nifty_symbol)
    nifty_returns = round((nifty_last_price - nifty_monday_open) / nifty_monday_open * 100, 2) if nifty_monday_open and nifty_last_price else None
    
    basket_returns = pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])["Returns (%)"].mean() if data else 0
    alpha = basket_returns - (nifty_returns if nifty_returns is not None else 0)
    
    display_alpha(alpha)
    return pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"]), alpha


# Get the table data
df, alpha = prepare_table_data()
df["Monday Open"] = df["Monday Open"].apply(lambda x: f"{x:.2f}" if x is not None else None)
df["Last Price"] = df["Last Price"].apply(lambda x: f"{x:.2f}" if x is not None else None)
df["Returns (%)"] = df["Returns (%)"].apply(lambda x: f"{x:.2f}%" if x is not None else None)

blank_row = pd.DataFrame([["", "", "", ""]], columns=df.columns)
df = pd.concat([df.iloc[:2], blank_row, df.iloc[2:]], ignore_index=True)

st.dataframe(df.style.map(color_returns, subset=["Returns (%)"]), use_container_width=True, hide_index=True)

# refresh_interval = st.slider("Refresh Interval - Minutes", min_value=1, max_value=60, value=5)
# st_autorefresh(interval=refresh_interval * 60000, key="refresh")
