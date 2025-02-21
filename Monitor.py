from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import pandas as pd

def get_most_recent_monday():
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    return monday.date()

def fetch_monday_open_price(ticker):
    try:
        monday = get_most_recent_monday()
        friday = monday - timedelta(days=3)  # Get data from Friday to ensure we have Monday's opening
        data = yf.download(ticker, start=friday, end=monday + timedelta(days=1))
        if not data.empty:
            # Get the first price of the week (Monday's open)
            return data["Open"].iloc[-1]
    except Exception as e:
        st.error(f"Error fetching Monday open price for {ticker}: {e}")
    return None

def fetch_last_price(ticker):
    try:
        data = yf.download(ticker, period="1d", interval="1d")
        if not data.empty:
            return data["Close"].iloc[-1]
    except Exception as e:
        st.error(f"Error fetching latest price for {ticker}: {e}")
    return None

def color_returns(val):
    if isinstance(val, str) and val.endswith("%"):
        returns = float(val.strip("%"))
        color = "green" if returns > 0 else "red"
        return f"color: {color}; text-align: right;"
    return ""

def display_alpha(alpha):
    color = "green" if alpha >= 0 else "red"
    st.markdown(
        f"<h1 style='text-align: center;'>Alpha: <span style='color: {color};'>{alpha:.2f}%</span></h1>",
        unsafe_allow_html=True
    )

def prepare_table_data(tickers):
    nifty_symbol = "^CRSLDX"  # Nifty 500 equivalent
    data = []
    
    for ticker in tickers:
        ticker_symbol = f"{ticker}.NS"
        monday_open = fetch_monday_open_price(ticker_symbol)
        last_price = fetch_last_price(ticker_symbol)
        
        if monday_open is not None and last_price is not None:
            returns = ((last_price - monday_open) / monday_open) * 100
            returns = round(float(returns), 2)
            data.append([ticker, round(monday_open, 2), round(last_price, 2), returns])

    # Fetch Nifty 500 data
    nifty_monday_open = fetch_monday_open_price(nifty_symbol)
    nifty_last_price = fetch_last_price(nifty_symbol)
    
    if nifty_monday_open is not None and nifty_last_price is not None:
        nifty_returns = round((nifty_last_price - nifty_monday_open) / nifty_monday_open * 100, 2)
        basket_returns = pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])["Returns (%)"].mean() if data else 0
        alpha = basket_returns - nifty_returns

        # Add summary rows
        summary_data = [
            ["Intraweek", 0, 0, round(basket_returns, 2)],
            ["Nifty 500", round(nifty_monday_open, 2), round(nifty_last_price, 2), nifty_returns]
        ]
        
        # Combine summary and stock data
        data = summary_data + data
        
        df = pd.DataFrame(data, columns=["Ticker", "Monday Open", "Last Price", "Returns (%)"])
        
        # Format numbers
        df["Monday Open"] = df["Monday Open"].apply(lambda x: f"{x:.2f}")
        df["Last Price"] = df["Last Price"].apply(lambda x: f"{x:.2f}")
        df["Returns (%)"] = df["Returns (%)"].apply(lambda x: f"{x:.2f}%")
        
        # Insert blank row after summary
        blank_row = pd.DataFrame([["", "", "", ""]], columns=df.columns)
        df = pd.concat([df.iloc[:2], blank_row, df.iloc[2:]], ignore_index=True)
        
        return df, alpha
    
    return None, None

# Streamlit app
st.title("Stock Portfolio Tracker")

# File uploader for new stocks
uploaded_file = st.file_uploader("Upload new stock list (CSV)", type="csv")
if uploaded_file is not None:
    # Read the uploaded CSV
    new_tickers = pd.read_csv(uploaded_file, header=None)[0].tolist()
    # Remove .NS extension if present
    new_tickers = [ticker.replace(".NS", "") for ticker in new_tickers]
    # Save to stk.csv
    pd.DataFrame(new_tickers).to_csv("stk.csv", index=False, header=False)
    st.success("Stock list updated successfully!")

# Read current tickers
try:
    tickers = pd.read_csv("stk.csv", header=None)[0].tolist()
    tickers = [ticker.replace(".NS", "") for ticker in tickers]
except Exception as e:
    st.error("Error reading stock list. Please upload a CSV file.")
    tickers = []

if tickers:
    df, alpha = prepare_table_data(tickers)
    if df is not None and alpha is not None:
        display_alpha(alpha)
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
